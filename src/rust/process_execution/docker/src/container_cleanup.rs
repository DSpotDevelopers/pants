// Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
// Licensed under the Apache License, Version 2.0 (see LICENSE).

//! Remove an owned container and its disposable sandbox even after the container disappears.
use crate::docker::SANDBOX_BASE_PATH_IN_CONTAINER;
use bollard::container::RemoveContainerOptions;
use bollard::{Docker, errors::Error as DockerError};

/// Allocate one disposable sandbox and return its owned identity to the caller.
pub async fn create_sandbox_volume(docker: &Docker) -> Result<String, String> {
    let name = format!("pants-sandbox-{}", uuid::Uuid::new_v4());
    docker
        .create_volume(bollard::volume::CreateVolumeOptions {
            name: name.clone(),
            ..Default::default()
        })
        .await
        .map_err(|err| format!("Failed to create Docker sandbox volume: {err}"))?;
    Ok(name)
}

pub async fn remove_container(
    docker: &Docker,
    container_id: &str,
    owned_sandbox: Option<&str>,
    options: Option<RemoveContainerOptions>,
) -> Result<(), DockerError> {
    let sandbox = match owned_sandbox {
        Some(name) => Some(name.to_owned()),
        None => docker
            .inspect_container(container_id, None)
            .await?
            .mounts
            .unwrap_or_default()
            .into_iter()
            .find_map(|mount| {
                (mount.destination.as_deref() == Some(SANDBOX_BASE_PATH_IN_CONTAINER))
                    .then_some(mount.name)
                    .flatten()
                    .filter(|name| name.starts_with("pants-sandbox-"))
            }),
    };
    match docker.remove_container(container_id, options).await {
        Err(DockerError::DockerResponseServerError {
            status_code: 404, ..
        }) => (),
        result => result?,
    }
    if let Some(name) = sandbox {
        match docker.remove_volume(&name, None).await {
            Err(DockerError::DockerResponseServerError {
                status_code: 404, ..
            }) => (),
            result => result?,
        }
    }
    Ok(())
}
/// The two owned mounts recorded before a lifecycle test removes its container externally.
#[cfg(test)]
pub struct VolumeFixture(Vec<String>);

#[cfg(test)]
impl VolumeFixture {
    pub async fn snapshot(docker: &Docker, id: &str) -> Self {
        let names = docker
            .inspect_container(id, None)
            .await
            .unwrap()
            .mounts
            .unwrap()
            .into_iter()
            .filter_map(|mount| mount.name)
            .collect::<Vec<_>>();
        assert_eq!(names.len(), 2);
        Self(names)
    }
    pub async fn assert_present(&self, docker: &Docker) {
        for name in &self.0 {
            assert!(docker.inspect_volume(name).await.is_ok());
        }
    }
    pub async fn assert_released(&self, docker: &Docker) {
        for name in &self.0 {
            let result = docker.inspect_volume(name).await;
            if name.starts_with("pants-sandbox-") {
                assert!(
                    matches!(
                        result,
                        Err(DockerError::DockerResponseServerError {
                            status_code: 404,
                            ..
                        })
                    ),
                    "sandbox volume leaked: {name}"
                );
            } else {
                assert!(name.starts_with("pants-named-caches-"));
                assert!(result.is_ok(), "persistent cache removed: {name}");
            }
        }
    }
}

#[cfg(test)]
#[tokio::test]
async fn missing_container_cleanup_is_owned_idempotent_and_reports_errors() {
    use parking_lot::Mutex;
    use std::sync::Arc;
    use std::time::Duration;
    for volume_status in [
        "204 No Content",
        "404 Not Found",
        "500 Internal Server Error",
    ] {
        use std::io::{Read, Write};
        use std::net::TcpListener;
        use std::sync::atomic::{AtomicBool, Ordering};
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        listener.set_nonblocking(true).unwrap();
        let addr = listener.local_addr().unwrap();
        let stop = Arc::new(AtomicBool::new(false));
        let requests = Arc::new(Mutex::new(Vec::new()));
        let (stopped, seen) = (stop.clone(), requests.clone());
        let server = std::thread::spawn(move || {
            while !stopped.load(Ordering::SeqCst) {
                let (mut stream, _) = match listener.accept() {
                    Ok(value) => value,
                    Err(err) if err.kind() == std::io::ErrorKind::WouldBlock => {
                        std::thread::sleep(Duration::from_millis(1));
                        continue;
                    }
                    Err(err) => panic!("{err}"),
                };
                stream
                    .set_read_timeout(Some(Duration::from_secs(2)))
                    .unwrap();
                let mut data = Vec::new();
                while !data.windows(4).any(|bytes| bytes == b"\r\n\r\n") {
                    let mut buf = [0; 1024];
                    let count = stream.read(&mut buf).unwrap();
                    assert_ne!(count, 0);
                    data.extend_from_slice(&buf[..count]);
                }
                let request = String::from_utf8(data).unwrap();
                let line = request.lines().next().unwrap().to_owned();
                let (status, body) = if line.starts_with("DELETE ")
                    && line.contains("/volumes/pants-sandbox-probe")
                {
                    (
                        volume_status,
                        if volume_status.starts_with("204") {
                            ""
                        } else {
                            r#"{"message":"volume response"}"#
                        },
                    )
                } else {
                    assert!(
                        line.contains("/containers/lost"),
                        "unexpected request: {line}"
                    );
                    ("404 Not Found", r#"{"message":"container disappeared"}"#)
                };
                seen.lock().push(line);
                write!(stream, "HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}", body.len()).unwrap();
            }
        });
        let client =
            Docker::connect_with_http(&format!("http://{addr}"), 2, bollard::API_DEFAULT_VERSION)
                .unwrap();
        let result = remove_container(&client, "lost", Some("pants-sandbox-probe"), None).await;
        stop.store(true, Ordering::SeqCst);
        server.join().unwrap();
        assert_eq!(result.is_ok(), !volume_status.starts_with("500"));
        let requests = requests.lock();
        assert_eq!(requests.len(), 2);
        assert!(requests[0].starts_with("DELETE /containers/lost"));
        assert!(requests[1].starts_with("DELETE /volumes/pants-sandbox-probe"));
        assert!(
            !requests
                .iter()
                .any(|line| line.contains("pants-named-caches"))
        );
    }
}
