// Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
// Licensed under the Apache License, Version 2.0 (see LICENSE).
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;

use bytes::Bytes;
use fs::{DigestTrie, DirectoryDigest, TypedPath};
use hashing::Digest;
use parking_lot::Mutex;
use tempfile::TempDir;

use crate::{ImmutableInputs, ImmutableMaterializer, Store};

#[tokio::test]
async fn a_materializer_writes_an_immutable_input_and_this_process_writes_none_of_it() {
    // A tool's installed package store is an immutable input of many processes. Written by this process, each of
    // its files passes through this process's memory: the sandboxer writes it instead, as it writes sandboxes.
    let dir = TempDir::new().unwrap();
    let store = Store::local_only(task_executor::Executor::new(), dir.path().join("store")).unwrap();
    let bytes = Bytes::from("Hello, world!");
    store.store_file_bytes(bytes.clone(), false).await.unwrap();
    let files = HashMap::from([(PathBuf::from("pkg/index.js"), Digest::of_bytes(&bytes))]);
    let tree = DigestTrie::from_unique_paths(
        vec![TypedPath::File {
            path: files.keys().next().unwrap(),
            is_executable: false,
        }],
        &files,
    )
    .unwrap();
    // Not yet persisted: the materializer's process reads the tree from the store, so it must be recorded first.
    let digest: DirectoryDigest = tree.into();

    let calls: Arc<Mutex<Vec<(PathBuf, Digest)>>> = Arc::default();
    let seen = calls.clone();
    let materializer: ImmutableMaterializer = Arc::new(move |destination: PathBuf, _root: PathBuf, digest| {
        seen.lock().push((destination.clone(), digest.as_digest()));
        Box::pin(async move { std::fs::create_dir_all(&destination).map_err(|e| e.to_string()) })
    });
    let inputs = ImmutableInputs::new_with_materializer(
        store.clone(),
        &dir.path().join("inputs"),
        Some(materializer),
    )
    .unwrap();

    let path = inputs.path_for_dir(digest.clone()).await.unwrap();
    assert_eq!(*calls.lock(), vec![(path.clone(), digest.as_digest())]);
    assert!(path.is_dir());
    assert!(
        !path.join("pkg/index.js").exists(),
        "this process wrote the immutable input itself"
    );
    store
        .load_digest_trie(DirectoryDigest::from_persisted_digest(digest.as_digest()))
        .await
        .expect("the tree is in the store for the materializer's process");

    // Asked again, the same path, written once.
    assert_eq!(inputs.path_for_dir(digest).await.unwrap(), path);
    assert_eq!(calls.lock().len(), 1);
}
