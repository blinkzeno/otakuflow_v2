import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  createProject,
  deleteProject,
  listProjects,
} from "../services/api.ts";
import type { Project } from "../types/index.ts";
import AppShell from "../components/layout/AppShell.tsx";
import Badge from "../components/ui/Badge.tsx";
import Button from "../components/ui/Button.tsx";
import Card from "../components/ui/Card.tsx";
import EmptyState from "../components/ui/EmptyState.tsx";
import { Field, TextInput } from "../components/ui/Field.tsx";
import Icon from "../components/ui/Icon.tsx";
import Skeleton from "../components/ui/Skeleton.tsx";

export default function ProjectsPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [title, setTitle] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  async function reload(): Promise<void> {
    try {
      setProjects(await listProjects());
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
    }
  }

  useEffect(() => {
    void reload();
  }, []);

  async function onUpload(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    if (!file || !title.trim()) {
      setError("Pick a CBZ file and give the chapter a title.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const created = await createProject(file, title.trim());
      navigate(`/p/${created.project_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: number): Promise<void> {
    if (!window.confirm("Delete this project and its files?")) return;
    try {
      await deleteProject(id);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "delete failed");
    }
  }

  return (
    <AppShell title="Projects">
      <div className="space-y-6">
        <Card>
          <h2 className="font-semibold">New project</h2>
          <p className="mt-1 text-sm text-muted">
            Drop a chapter archive, get a narrated 1080p video out.
          </p>
          <form onSubmit={onUpload} className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <Field label="Chapter archive (.cbz, .zip)">
                <input
                  type="file"
                  accept=".cbz,.zip"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  className="w-full text-sm text-muted file:mr-3 file:rounded-md file:border file:border-line file:bg-raised file:px-3 file:py-1.5 file:text-sm file:text-ink hover:file:bg-line focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                />
              </Field>
            </div>
            <div className="flex-1">
              <Field label="Chapter title">
                <TextInput
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Chapter 12"
                />
              </Field>
            </div>
            <Button type="submit" disabled={busy}>
              {busy ? "Importing..." : "Import"}
            </Button>
          </form>
          {error && <p className="mt-2 text-sm text-bad">{error}</p>}
        </Card>

        <div>
          <h2 className="mb-3 font-semibold">Your chapters</h2>
          {projects === null ? (
            <Skeleton lines={4} />
          ) : projects.length === 0 ? (
            <EmptyState
              title="No project yet"
              hint="Import your first chapter above to start the pipeline."
            />
          ) : (
            <ul className="grid gap-3 sm:grid-cols-2">
              {projects.map((project) => (
                <li key={project.id}>
                  <Card className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <Link
                        to={`/p/${project.id}`}
                        className="block truncate font-medium hover:text-accent hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                      >
                        {project.title}
                      </Link>
                      <div className="mt-1.5 flex items-center gap-2">
                        <Badge tone="neutral">{project.status}</Badge>
                      </div>
                    </div>
                    <button
                      onClick={() => void onDelete(project.id)}
                      aria-label={`Delete ${project.title}`}
                      className="rounded-md p-2 text-muted hover:bg-raised hover:text-bad focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    >
                      <Icon name="trash" />
                    </button>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </AppShell>
  );
}
