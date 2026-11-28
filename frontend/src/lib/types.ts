export interface Feed {
  id: number;
  name: string;
  url: string;
  category: string;
  is_active: boolean;
  last_status: string; // "idle" | "active" | "error"
  last_fetched_at: string | null;
  created_at: string;
}

export interface FeedCreateInput {
  name: string;
  url: string;
  category?: string;
  is_active?: boolean;
}

export interface FeedUpdateInput {
  name?: string;
  url?: string;
  category?: string;
  is_active?: boolean;
}

export interface FeedTestSampleArticle {
  title: string;
  url: string;
  published_at?: string | null;
}

export interface FeedTestResult {
  valid: boolean;
  error?: string | null;
  title?: string | null;
  description?: string | null;
  item_count?: number;
  sample_articles?: FeedTestSampleArticle[];
}

export interface Article {
  id: number;
  feed_id?: number | null;
  title: string;
  url: string;
  snippet?: string | null;
  published_at?: string | null;
  created_at: string;
}

export interface Digest {
  id: number;
  date: string; // YYYY-MM-DD
  summary_markdown: string;
  summary_html: string;
  model_used: string;
  total_clusters: number;
  total_sources: number;
  status: "draft" | "published" | "broadcasted";
  broadcasted_at?: string | null;
  created_at: string;
}

export interface DigestListResponse {
  items: Digest[];
  total: number;
  page: number;
  pages: number;
  limit: number;
}

export interface PipelineRun {
  id: string;
  trigger_type: "scheduled" | "manual";
  status: "running" | "completed" | "failed";
  logs?: string | null; // JSON string of logs
  started_at: string;
  completed_at?: string | null;
}

export interface OverviewMetrics {
  active_feeds_count: number;
  total_feeds_count: number;
  articles_today_count: number;
  total_digests_count: number;
  last_run: {
    id: string | null;
    status: string;
    trigger_type: string | null;
    started_at: string | null;
    completed_at: string | null;
  } | null;
  latest_digest: {
    id: number | null;
    date: string | null;
    status: string | null;
    total_clusters: number;
    total_sources: number;
    model_used: string | null;
    broadcasted_at: string | null;
  } | null;
}

export interface PipelineEvent {
  event: string;
  stage?: string;
  progress?: number;
  message?: string;
  timestamp?: string;
  run_id?: string;
  feed?: string;
  total_clusters?: number;
  model?: string;
  digest_id?: number;
  date?: string;
}
