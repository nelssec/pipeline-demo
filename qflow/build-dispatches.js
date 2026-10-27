// Turns Container Security containers with PHP2Shell into GitHub repository_dispatch
// requests for the repo that built each image. One request per image, not per container.
async function process() {
  // Repos this QFlow may dispatch to. Anything else is reported but not dispatched.
  const ALLOWED_REPOS = ["nelssec/pipeline-demo"];
  // 389102 = PHP (upstream), 6877310 = Ubuntu USN-8948-1. Keep in sync with node 2's filter.
  const QIDS = [389102, 6877310];
  const SOURCE_LABEL = "org.opencontainers.image.source";
  const REVISION_LABEL = "org.opencontainers.image.revision";

  const label = (c, key) => {
    const labels = c.labels || c.imageLabels || (c.image && c.image.labels) || [];
    if (Array.isArray(labels)) {
      const hit = labels.find((l) => l && (l.key === key || l.name === key));
      return hit ? String(hit.value || "") : "";
    }
    return labels[key] ? String(labels[key]) : "";
  };

  // owner/repo from the OCI source label, else from a ghcr.io/<owner>/<repo>/... image path.
  const repoFor = (c, imageRef) => {
    const m1 = label(c, SOURCE_LABEL).match(/github\.com\/([^/]+\/[^/.]+)/i);
    if (m1) return m1[1].toLowerCase();
    const m2 = imageRef.match(/^ghcr\.io\/([^/]+\/[^/:@]+)/i);
    return m2 ? m2[1].toLowerCase() : "";
  };

  // Container Security returns one page per call ({count, data: [...]}); take the containers from each page.
  const containers = (Array.isArray(context.collection) ? context.collection : []).flatMap((p) => (p && Array.isArray(p.data) ? p.data : [p]));
  const seen = {};
  const result = [];
  for (const c of containers) {
    const sha = String(c.imageSha || c.imageId || c.sha || "").replace(/^sha256:/, "");
    const repoTag = c.imageRepo || c.repository || (c.image && c.image.repo) || "";
    const imageRef = String(c.image || c.imageName || repoTag || "");
    const repo = repoFor(c, imageRef);
    if (!repo || seen[repo + sha]) continue;
    seen[repo + sha] = true;

    const base = imageRef.split("@")[0].replace(/:[^/:]+$/, "");
    const image = /^[0-9a-f]{64}$/.test(sha) && base ? `${base}@sha256:${sha}` : imageRef;
    const vulns = Array.isArray(c.vulnerabilities) ? c.vulnerabilities : [];
    const found = vulns.map((v) => Number(v && v.qid)).find((q) => QIDS.includes(q));
    result.push({
      repo,
      dispatch: ALLOWED_REPOS.includes(repo),
      qid: String(found || QIDS[1]),
      image,
      revision: label(c, REVISION_LABEL),
      container_id: String(c.containerId || c.uuid || ""),
      host: String((c.host && (c.host.hostname || c.host.ipAddress)) || c.cluster || c.hostname || ""),
    });
  }
  exit(null, result.filter((r) => r.dispatch));
}
process().catch(exit);
