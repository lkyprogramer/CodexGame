# Repository instructions for development agents

This bundle is a plan and verified helper toolkit, not a completed inference-engine port.
Read AGENT_START.md before touching a GPU or production service.

- Preserve the exact original Java fixtures (references/fixture-lock.json).
- Use explicit data provenance. Imported reports are not freshly executed measurements.
- Never replace the production artifact or expose credentials.
- CPU tools use the Python standard library. GPU dependencies belong to the pinned container.
- Never reinterpret skipped, missing, timeout or NOT_IMPLEMENTED results as PASS.
- Do not relax sampling, model quality, 200192 protected capacity (docs/02 §3) or state-consistency constraints for speed.
- Build the smallest independent patch and keep a rollback tag.
- Keep proposed interfaces clearly separate from existing upstream functions.
- Hold one authorized GPU lease. Pi and Java tests run on the Mac controller.
- Any production promotion, privilege expansion, external data upload, overclock or paid compute requires explicit approval.
