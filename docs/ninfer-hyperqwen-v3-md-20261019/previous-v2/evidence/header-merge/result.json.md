# V2 支撑材料：`evidence/header-merge/result.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: evidence/header-merge/result.json -->
<!-- payload-sha256: eb4e906b079a724674c399615bfa77df57b54c4a74553ba6af39b81c0e3d201c -->
<!-- payload-bytes: 1470 -->

<!-- payload-begin -->
````json
{
  "scope": "complete tokenizer.h only, NOT full repository merge",
  "git_version": "git version 2.47.3",
  "command": [
    "git",
    "merge-file",
    "--diff3",
    "-p",
    "-L",
    "OURS e0b05f7",
    "-L",
    "BASE 44a2c6c",
    "-L",
    "UPSTREAM 5b99996",
    "/mnt/data/ninfer_merge_audit/package/evidence/header-merge/ours.tokenizer.h",
    "/mnt/data/ninfer_merge_audit/package/evidence/header-merge/base.tokenizer.h",
    "/mnt/data/ninfer_merge_audit/package/evidence/header-merge/upstream.tokenizer.h"
  ],
  "returncode": 2,
  "conflict_hunks": 2,
  "source_blobs": [
    {
      "side": "base",
      "file": "base.tokenizer.h",
      "git_blob_sha1": "e90338a3d5d7bfad98aec62269616dcf8a000f39",
      "sha256": "9fc3a711e382b3e1460a37f4f2dbc50669bf7b915413008c3c6d8960c47576e1",
      "verified_against_connector_blob": true
    },
    {
      "side": "ours",
      "file": "ours.tokenizer.h",
      "git_blob_sha1": "6f1858ac29b84c82eae1f9ed204dea0c33a081c6",
      "sha256": "cd63082349e8f92f2b767c07a9355a545f213c6d74c79ef8d1b8d9a85f657e77",
      "verified_against_connector_blob": true
    },
    {
      "side": "upstream",
      "file": "upstream.tokenizer.h",
      "git_blob_sha1": "982bb4eaf3e1d5d913927da2a1a812213b3dddae",
      "sha256": "b3486d178a24a4b9b2795bd18a951e426b40673ceec1e6cb9742434be472f2f3",
      "verified_against_connector_blob": true
    }
  ],
  "compilation_executed": false,
  "gpu_validation_executed": false
}
````
<!-- payload-end -->
