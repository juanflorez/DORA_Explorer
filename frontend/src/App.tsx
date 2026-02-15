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

interface EnvironmentItem {
  id: number;
  name: string;
}

interface DeploymentRecord {
  id: number;
  pipeline_name: string;
  result: string;
  started_on: string;
  finished_on: string;
}

type Step = "credentials" | "project" | "repo" | "environment" | "deployments";

const STEPS: Step[] = [
  "credentials",
  "project",
  "repo",
  "environment",
  "deployments",
];

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

  const [environments, setEnvironments] = useState<EnvironmentItem[]>([]);
  const [selectedEnvId, setSelectedEnvId] = useState<number | "">("");

  const [deployments, setDeployments] = useState<DeploymentRecord[]>([]);

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

  async function fetchReposAndEnvs() {
    setError("");
    setLoading(true);
    try {
      const [repoData, envData] = await Promise.all([
        postApi<RepoItem[]>("/repos", { org, pat, project: selectedProject }),
        postApi<EnvironmentItem[]>("/environments", {
          org,
          pat,
          project: selectedProject,
        }),
      ]);
      setRepos(repoData);
      setEnvironments(envData);
      setStep("repo");
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Failed to fetch repos/environments"
      );
    } finally {
      setLoading(false);
    }
  }

  async function fetchDeployments() {
    setError("");
    setLoading(true);
    try {
      const data = await postApi<DeploymentRecord[]>("/deployments", {
        org,
        pat,
        project: selectedProject,
        environment_id: selectedEnvId,
      });
      setDeployments(data);
      setStep("deployments");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to fetch deployments");
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setStep("credentials");
    setProjects([]);
    setRepos([]);
    setEnvironments([]);
    setDeployments([]);
    setSelectedProject("");
    setSelectedRepo("");
    setSelectedEnvId("");
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
          <button
            onClick={fetchProjects}
            disabled={loading || !org || !pat}
          >
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
            onClick={fetchReposAndEnvs}
            disabled={loading || !selectedProject}
          >
            {loading ? "Loading…" : "Next"}
          </button>
        </div>
      )}

      {step === "repo" && (
        <div className="card">
          <button
            className="back-link"
            onClick={() => setStep("project")}
          >
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
            onClick={() => setStep("environment")}
            disabled={!selectedRepo}
          >
            Next
          </button>
        </div>
      )}

      {step === "environment" && (
        <div className="card">
          <button
            className="back-link"
            onClick={() => setStep("repo")}
          >
            ← Back to repo
          </button>
          <label htmlFor="env">Select Deployment Environment</label>
          <select
            id="env"
            value={selectedEnvId}
            onChange={(e) => setSelectedEnvId(Number(e.target.value))}
          >
            <option value="">-- choose --</option>
            {environments.map((env) => (
              <option key={env.id} value={env.id}>
                {env.name}
              </option>
            ))}
          </select>
          <button
            onClick={fetchDeployments}
            disabled={loading || selectedEnvId === ""}
          >
            {loading ? "Loading…" : "Fetch Deployments"}
          </button>
        </div>
      )}

      {step === "deployments" && (
        <div className="card">
          <button className="back-link" onClick={() => setStep("environment")}>
            ← Back to environment
          </button>
          <h2 style={{ marginBottom: "0.75rem", fontSize: "1.125rem" }}>
            Deployments — past 6 months
          </h2>
          {deployments.length === 0 ? (
            <p>No deployments found.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Pipeline</th>
                  <th>Result</th>
                  <th>Started</th>
                  <th>Finished</th>
                </tr>
              </thead>
              <tbody>
                {deployments.map((d) => (
                  <tr key={d.id}>
                    <td>{d.pipeline_name}</td>
                    <td>
                      <span
                        className={`result-badge ${d.result === "succeeded" ? "succeeded" : "failed"}`}
                      >
                        {d.result}
                      </span>
                    </td>
                    <td>{new Date(d.started_on).toLocaleString()}</td>
                    <td>{new Date(d.finished_on).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p style={{ marginTop: "0.75rem", fontSize: "0.8125rem", color: "#6b7280" }}>
            Total: {deployments.length} deployment{deployments.length !== 1 && "s"}
          </p>
        </div>
      )}
    </div>
  );
}

export default App;
