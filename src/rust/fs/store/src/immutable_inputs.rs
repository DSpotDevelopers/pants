// Copyright 2022 Pants project contributors (see CONTRIBUTORS.md).
// Licensed under the Apache License, Version 2.0 (see LICENSE).
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fs::create_dir_all;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use async_oncecell::OnceCell;
use fs::{DirectoryDigest, Permissions, RelativePath};
use futures::future::BoxFuture;
use hashing::Digest;
use parking_lot::Mutex;
use tempfile::TempDir;

use crate::{Store, StoreError};

/// A symlink from a relative src to an absolute dst (outside of the workdir).
#[derive(Debug)]
pub struct WorkdirSymlink {
    pub src: RelativePath,
    pub dst: PathBuf,
}

/// Writes a persisted directory digest, read-only, at a destination under a root, in another process (the
/// sandboxer): an immutable input such as a tool's installed package store then never passes through this
/// process's memory.
pub type ImmutableMaterializer = Arc<
    dyn Fn(PathBuf, PathBuf, DirectoryDigest) -> BoxFuture<'static, Result<(), String>>
        + Send
        + Sync,
>;

struct Inner {
    store: Store,
    // Writes each digest in another process when set; this process writes it otherwise.
    materializer: Option<ImmutableMaterializer>,
    // The TempDir that digests are materialized in.
    workdir: TempDir,
    // A map from Digest to the location it has been materialized at. The OnceCell allows
    // for cooperation between threads attempting to create Digests.
    contents: Mutex<HashMap<Digest, Arc<OnceCell<PathBuf>>>>,
}

///
/// Holds Digests materialized into a temporary directory, for symlinking into local sandboxes.
///
#[derive(Clone)]
pub struct ImmutableInputs(Arc<Inner>);

impl ImmutableInputs {
    pub fn new(store: Store, base: &Path) -> Result<Self, String> {
        Self::new_with_materializer(store, base, None)
    }

    pub fn new_with_materializer(
        store: Store,
        base: &Path,
        materializer: Option<ImmutableMaterializer>,
    ) -> Result<Self, String> {
        create_dir_all(base)
            .map_err(|e| format!("Failed to create base for immutable inputs: {e}"))?;
        let workdir = tempfile::Builder::new()
            .prefix("immutable_inputs")
            .tempdir_in(base)
            .map_err(|e| {
                format!("Failed to create temporary directory for immutable inputs: {e}")
            })?;
        Ok(Self(Arc::new(Inner {
            store,
            materializer,
            workdir,
            contents: Mutex::default(),
        })))
    }

    pub fn workdir(&self) -> &Path {
        self.0.workdir.path()
    }

    /// Returns an absolute Path to immutably consume the given Digest from.
    pub(crate) async fn path_for_dir(
        &self,
        directory_digest: DirectoryDigest,
    ) -> Result<PathBuf, StoreError> {
        let digest = directory_digest.as_digest();
        let cell = self.0.contents.lock().entry(digest).or_default().clone();

        // We (might) need to initialize the value.
        //
        // Because this code executes a side effect which could be observed elsewhere within this
        // process (other threads can observe the contents of the temporary directory), we need to
        // ensure that if this method is cancelled (via async Drop), whether the cell has been
        // initialized or not stays in sync with whether the side effect is visible.
        //
        // Making the initialization "cancellation safe", involves either:
        //
        //   1. Adding a Drop guard to "undo" the side effect if we're dropped before we fully
        //      initialize the cell.
        //       * This is challenging to do correctly in this case, because the `Drop` guard cannot
        //         be created until after initialization begins, but cannot be cleared until after the
        //         cell has been initialized (i.e., after `get_or_try_init` returns).
        //   2. Shielding ourselves from cancellation by `spawn`ing a new Task to guarantee that the
        //      cell initialization always runs to completion.
        //       * This would work, but would mean that we would finish initializing cells even when
        //         work was cancelled. Cancellation usually means that the work is no longer necessary,
        //         and so that could result in a lot of spurious IO (in e.g. warm cache cases which
        //         never end up actually needing any inputs).
        //       * An advanced variant of this approach would be to _pause_ work on materializing a
        //         Digest when demand for it disappeared, and resume the work if another caller
        //         requested that Digest.
        //   3. Using anonymous destination paths, such that multiple attempts to initialize cannot
        //      collide.
        //       * This means that although the side effect is visible, it can never collide.
        //
        // We take the final approach here currently (for simplicity's sake), but the advanced variant
        // of approach 2 might eventually be worthwhile.
        cell.get_or_try_init(async {
            let chroot = TempDir::new_in(self.0.workdir.path()).map_err(|e| {
                format!(
                    "Failed to create a temporary directory for materialization of immutable input \
            digest {digest:?}: {e}"
                )
            })?;

            let dest = chroot.path().join(digest.hash.to_hex());
            if let Some(materializer) = &self.0.materializer {
                // The other process reads the tree from the store: record it there first.
                let persisted = DirectoryDigest::from_persisted_digest(digest);
                if let Some(tree) = directory_digest.tree {
                    self.0.store.record_digest_trie(tree, true).await?;
                }
                materializer(dest.clone(), self.0.workdir.path().to_path_buf(), persisted)
                    .await
                    .map_err(|e| {
                        format!(
                            "Failed to materialize immutable input digest {digest:?} in another \
                            process: {e}"
                        )
                    })?;
            } else {
                self.0
                    .store
                    .materialize_directory(
                        dest.clone(),
                        self.0.workdir.path(),
                        directory_digest,
                        false,
                        &BTreeSet::new(),
                        Permissions::ReadOnly,
                    )
                    .await?;
            }

            // Now that we've successfully initialized the destination, forget the TempDir so that it
            // is not cleaned up.
            let _ = chroot.keep();

            Ok(dest)
        })
        .await
        .cloned()
    }

    ///
    /// Returns symlinks to create for the given set of immutable cache paths.
    ///
    pub async fn local_paths(
        &self,
        immutable_inputs: &BTreeMap<RelativePath, DirectoryDigest>,
    ) -> Result<Vec<WorkdirSymlink>, StoreError> {
        let dsts = futures::future::try_join_all(
            immutable_inputs
                .values()
                .map(|d| self.path_for_dir(d.clone()))
                .collect::<Vec<_>>(),
        )
        .await?;

        Ok(immutable_inputs
            .keys()
            .zip(dsts)
            .map(|(src, dst)| WorkdirSymlink {
                src: src.clone(),
                dst,
            })
            .collect())
    }
}
