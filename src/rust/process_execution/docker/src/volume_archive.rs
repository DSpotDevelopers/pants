// Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
// Licensed under the Apache License, Version 2.0 (see LICENSE).

//! Docker's archive API transfers a sandbox without interpreting its path on the daemon host.
use std::io;
use std::path::{Component, Path};

pub fn pack_directory(path: &Path) -> io::Result<Vec<u8>> {
    let mut archive = tar::Builder::new(Vec::new());
    archive.follow_symlinks(false);
    let root = path
        .file_name()
        .ok_or_else(|| io::Error::other("Missing sandbox name"))?;
    archive.append_dir_all(root, path)?;
    archive.into_inner()
}

pub fn restore_directory(bytes: &[u8], path: &Path) -> io::Result<()> {
    let root = path
        .file_name()
        .ok_or_else(|| io::Error::other("Missing sandbox name"))?;
    let parent = path
        .parent()
        .ok_or_else(|| io::Error::other("Missing sandbox parent"))?;
    let staging = tempfile::tempdir_in(parent)?;
    for entry in tar::Archive::new(bytes).entries()? {
        let mut entry = entry?;
        let name = entry.path()?;
        let kind = entry.header().entry_type();
        if !name.starts_with(Path::new(root))
            || name.components().any(|c| {
                matches!(
                    c,
                    Component::ParentDir | Component::RootDir | Component::Prefix(_)
                )
            })
            || !(kind.is_file() || kind.is_dir() || kind.is_symlink() || kind.is_hard_link())
        {
            return Err(io::Error::other("Invalid Docker sandbox archive entry"));
        }
        if !entry.unpack_in(staging.path())? {
            return Err(io::Error::other("Docker sandbox archive escaped its root"));
        }
    }
    let captured = staging.path().join(root);
    if !captured.symlink_metadata()?.is_dir() {
        return Err(io::Error::other(
            "Docker sandbox archive has no directory root",
        ));
    }
    // Unlink original inputs before replacing them: they may be hardlinks into the local CAS.
    // Staging also ensures deleted inputs do not survive a merge-style extraction.
    std::fs::remove_dir_all(path)?;
    std::fs::rename(captured, path)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::os::unix::fs::{PermissionsExt, symlink};

    #[test]
    fn round_trip_replaces_deleted_inputs_without_mutating_cas_links() {
        let local = tempfile::tempdir().unwrap();
        let workdir = local.path().join("sandbox");
        fs::create_dir(&workdir).unwrap();
        let cas = local.path().join("cas");
        fs::write(&cas, b"original").unwrap();
        fs::hard_link(&cas, workdir.join("tool")).unwrap();
        fs::write(workdir.join("deleted"), b"removed by process").unwrap();

        let remote = tempfile::tempdir().unwrap();
        let sandbox = remote.path().join("sandbox");
        fs::create_dir(&sandbox).unwrap();
        fs::write(sandbox.join("tool"), b"output").unwrap();
        fs::set_permissions(sandbox.join("tool"), fs::Permissions::from_mode(0o755)).unwrap();
        symlink("tool", sandbox.join("link")).unwrap();
        symlink("/pants-named-caches/cache", sandbox.join("cache")).unwrap();
        let bytes = pack_directory(&sandbox).unwrap();
        restore_directory(&bytes, &workdir).unwrap();

        assert!(!workdir.join("deleted").exists());
        assert_eq!(fs::read(&cas).unwrap(), b"original");
        assert_eq!(fs::read(workdir.join("link")).unwrap(), b"output");
        assert_eq!(
            fs::read_link(workdir.join("cache")).unwrap(),
            Path::new("/pants-named-caches/cache")
        );
        assert_eq!(
            fs::metadata(workdir.join("tool"))
                .unwrap()
                .permissions()
                .mode()
                & 0o777,
            0o755
        );
    }

    #[test]
    fn foreign_root_is_refused_without_changing_existing_sandbox() {
        let local = tempfile::tempdir().unwrap();
        let workdir = local.path().join("sandbox");
        fs::create_dir(&workdir).unwrap();
        fs::write(workdir.join("kept"), b"input").unwrap();
        let remote = tempfile::tempdir().unwrap();
        let foreign = remote.path().join("other-sandbox");
        fs::create_dir(&foreign).unwrap();
        fs::write(foreign.join("outside"), b"wrong root").unwrap();
        assert!(restore_directory(&pack_directory(&foreign).unwrap(), &workdir).is_err());
        assert_eq!(fs::read(workdir.join("kept")).unwrap(), b"input");
        assert!(!local.path().join("other-sandbox").exists());
    }
}

#[cfg(test)]
mod refusal_tests {
    use super::*;
    use std::fs;

    #[test]
    fn symlink_traversal_never_writes_outside_the_staged_root() {
        let local = tempfile::tempdir().unwrap();
        let sandbox = local.path().join("sandbox");
        let outside = local.path().join("outside");
        fs::create_dir(&sandbox).unwrap();
        fs::create_dir(&outside).unwrap();
        let mut archive = tar::Builder::new(Vec::new());
        let mut header = tar::Header::new_gnu();
        header.set_entry_type(tar::EntryType::Symlink);
        header.set_size(0);
        header.set_mode(0o777);
        archive
            .append_link(&mut header, "sandbox/escape", &outside)
            .unwrap();
        let mut file = tar::Header::new_gnu();
        file.set_size(4);
        file.set_mode(0o644);
        file.set_cksum();
        archive
            .append_data(&mut file, "sandbox/escape/written", &b"nope"[..])
            .unwrap();
        assert!(restore_directory(&archive.into_inner().unwrap(), &sandbox).is_err());
        assert!(!outside.join("written").exists());
        assert!(sandbox.is_dir());
    }

    #[test]
    fn special_files_are_refused_before_touching_the_original_sandbox() {
        let local = tempfile::tempdir().unwrap();
        let sandbox = local.path().join("sandbox");
        fs::create_dir(&sandbox).unwrap();
        fs::write(sandbox.join("original"), b"kept").unwrap();
        let mut archive = tar::Builder::new(Vec::new());
        let mut header = tar::Header::new_gnu();
        header.set_entry_type(tar::EntryType::Fifo);
        header.set_size(0);
        header.set_mode(0o600);
        header.set_cksum();
        archive
            .append_data(&mut header, "sandbox/fifo", &b""[..])
            .unwrap();
        assert!(restore_directory(&archive.into_inner().unwrap(), &sandbox).is_err());
        assert_eq!(fs::read(sandbox.join("original")).unwrap(), b"kept");
    }
}
