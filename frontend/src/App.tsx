import { useState } from "react";
import "./App.css";

interface ProjectItem {
  id: string;
  name: string;
}

interface RepoItem {
  id: string;
  name: string;
}

interface PipelineItem {
  id: number;
  name: string;
}

interface BuildRecord {
  id: number;
  build_number: string;
  pipeline_name: string;
  result: string;
  status: string;
  started_on: string;
  finished_on: string;
}

type Step = "credentials" | "project" | "repo" | "pipeline" | "builds";

const STEPS: Step[] = ["credentials", "project", "repo", "pipeline", "builds"];

function stepIndex(step: Step) {
  return STEPS.indexOf(step);
}

function App() {
  const [step, setStep] = useState<Step>("credentials");
  const [org, setOrg] = useState("");
  const [pat, setPat] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [selectedProject, setSelectedProject] = useState("");

  const [repos, setRepos] = useState<RepoItem[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");

  const [pipelines, setPipelines] = useState<PipelineItem[]>([]);
  const [selectedPipelineId, setSelectedPipelineId] = useState<number | "">("");

  const [builds, setBuilds] = useState<BuildRecord[]>([]);

  async function postApi<T>(path: string, body: object): Promise<T> {
    const resp = await fetch(`/api${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      throw new Error(detail || `Request failed (${resp.status})`);
    }
    return resp.json();
  }

  async function fetchProjects() {
    setError("");
    setLoading(true);
    try {
      const data = await postApi<ProjectItem[]>("/projects", { org, pat });
      setProjects(data);
      setStep("project");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to fetch projects");
    } finally {
      setLoading(false);
    }
  }

  async function fetchReposAndPipelines() {
    setError("");
    setLoading(true);
    try {
      const [repoData, pipelineData] = await Promise.all([
        postApi<RepoItem[]>("/repos", { org, pat, project: selectedProject }),
        postApi<PipelineItem[]>("/pipelines", {
          org,
          pat,
          project: selectedProject,
        }),
      ]);
      setRepos(repoData);
      setPipelines(pipelineData);
      setStep("repo");
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Failed to fetch repos/pipelines"
      );
    } finally {
      setLoading(false);
    }
  }

  async function fetchBuilds() {
    setError("");
    setLoading(true);
    try {
      const data = await postApi<BuildRecord[]>("/builds", {
        org,
        pat,
        project: selectedProject,
        definition_id: selectedPipelineId,
      });
      setBuilds(data);
      setStep("builds");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to fetch builds");
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setStep("credentials");
    setProjects([]);
    setRepos([]);
    setPipelines([]);
    setBuilds([]);
    setSelectedProject("");
    setSelectedRepo("");
    setSelectedPipelineId("");
    setError("");
  }

  const currentIdx = stepIndex(step);

  return (
    <div className="app">
      <h1>AzTrial — DORA Metrics Tracker</h1>

      <div className="step-indicator">
        {STEPS.map((s, i) => (
          <div
            key={s}
            className={`step-dot ${i === currentIdx ? "active" : ""} ${i < currentIdx ? "done" : ""}`}
          />
        ))}
      </div>

      {error && <p className="error">{error}</p>}

      {step === "credentials" && (
        <div className="card">
          <label htmlFor="org">Azure DevOps Organization</label>
          <input
            id="org"
            value={org}
            onChange={(e) => setOrg(e.target.value)}
            placeholder="my-org"
          />
          <label htmlFor="pat">Personal Access Token</label>
          <input
            id="pat"
            type="password"
            value={pat}
            onChange={(e) => setPat(e.target.value)}
            placeholder="paste your PAT"
          />
          <button onClick={fetchProjects} disabled={loading || !org || !pat}>
            {loading ? "Connecting…" : "Connect"}
          </button>
        </div>
      )}

      {step === "project" && (
        <div className="card">
          <button className="back-link" onClick={reset}>
            ← Change credentials
          </button>
          <label htmlFor="project">Select Project</label>
          <select
            id="project"
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
          >
            <option value="">-- choose --</option>
            {projects.map((p) => (
              <option key={p.id} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
          <button
            onClick={fetchReposAndPipelines}
            disabled={loading || !selectedProject}
          >
            {loading ? "Loading…" : "Next"}
          </button>
        </div>
      )}

      {step === "repo" && (
        <div className="card">
          <button className="back-link" onClick={() => setStep("project")}>
            ← Back to project
          </button>
          <label htmlFor="repo">Select Repository</label>
          <select
            id="repo"
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
          >
            <option value="">-- choose --</option>
            {repos.map((r) => (
              <option key={r.id} value={r.name}>
                {r.name}
              </option>
            ))}
          </select>
          <button
            onClick={() => setStep("pipeline")}
            disabled={!selectedRepo}
          >
            Next
          </button>
        </div>
      )}

      {step === "pipeline" && (
        <div className="card">
          <button className="back-link" onClick={() => setStep("repo")}>
            ← Back to repo
          </button>
          <label htmlFor="pipeline">Select Pipeline</label>
          <select
            id="pipeline"
            value={selectedPipelineId}
            onChange={(e) => setSelectedPipelineId(Number(e.target.value))}
          >
            <option value="">-- choose --</option>
            {pipelines.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <button
            onClick={fetchBuilds}
            disabled={loading || selectedPipelineId === ""}
          >
            {loading ? "Loading…" : "Fetch Builds"}
          </button>
        </div>
      )}

      {step === "builds" && (
        <div className="card">
          <button className="back-link" onClick={() => setStep("pipeline")}>
            ← Back to pipeline
          </button>
          <h2 style={{ marginBottom: "0.75rem", fontSize: "1.125rem" }}>
            Builds — past 6 months
          </h2>
          {builds.length === 0 ? (
            <p>No builds found.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Pipeline</th>
                  <th>Build #</th>
                  <th>Result</th>
                  <th>Started</th>
                  <th>Finished</th>
                </tr>
              </thead>
              <tbody>
                {builds.map((b) => (
                  <tr key={b.id}>
                    <td>{b.pipeline_name}</td>
                    <td>{b.build_number}</td>
                    <td>
                      <span
                        className={`result-badge ${b.result === "succeeded" ? "succeeded" : "failed"}`}
                      >
                        {b.result}
                      </span>
                    </td>
                    <td>{new Date(b.started_on).toLocaleString()}</td>
                    <td>{new Date(b.finished_on).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p
            style={{
              marginTop: "0.75rem",
              fontSize: "0.8125rem",
              color: "#6b7280",
            }}
          >
            Total: {builds.length} build{builds.length !== 1 && "s"}
          </p>
        </div>
      )}
    </div>
  );
}

export default App;
