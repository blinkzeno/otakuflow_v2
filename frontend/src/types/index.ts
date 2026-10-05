// Shared shapes. They mirror the JSON the API sends. No any anywhere.

export interface Project {
  id: number;
  title: string;
  status: string;
  created_at: string;
}

export interface Chapter {
  id: number;
  project_id: number;
  title: string;
  source_filename: string;
  page_count: number;
  reading_order: string;
  chapter_summary: string | null;
}

export interface Job {
  id: number;
  project_id: number;
  stage: string;
  status: string;
  progress: number;
  error: string | null;
}

export interface ProjectDetail {
  project: Project;
  chapters: Chapter[];
  jobs: Job[];
}

export interface Page {
  id: number;
  chapter_id: number;
  page_index: number;
  page_id: string;
  filename: string;
  rel_path: string;
  width: number | null;
  height: number | null;
  analysis_json: string | null;
  importance: number | null;
  analysis_status: string;
  analysis_error: string | null;
}

export interface CreateResult {
  project_id: number;
  job_id: number;
}

export interface Dialogue {
  speaker: string | null;
  text: string;
}

export interface PageAnalysis {
  characters: string[];
  actions: string[];
  dialogues: Dialogue[];
  events: string[];
  location: string;
  importance: number;
  summary: string;
  visual_description: string;
}

export interface QuotaBucket {
  model: string;
  used: number;
  cap: number;
}

export interface Quota {
  vision: QuotaBucket;
  text: QuotaBucket;
}

export interface ScriptSegment {
  id: number;
  chapter_id: number;
  position: number;
  segment_key: string;
  text: string;
  page_refs: number[];
  duration_estimate: number | null;
  status: string;
}

export interface FocusBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface TimelinePage {
  id: number;
  index: number;
  focus: FocusBox | null;
}

export interface TimelineClip {
  segment_key: string;
  position: number;
  start: number;
  duration: number;
  audio_rel: string;
  pages: TimelinePage[];
}

export interface Timeline {
  clips: TimelineClip[];
  total: number;
}

export interface RenderInfo {
  id: number;
  chapter_id: number;
  timeline_json: string;
  video_rel_path: string | null;
  settings_json: string;
  status: string;
}
