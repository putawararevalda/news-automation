import {
  Feed,
  FeedCreateInput,
  FeedUpdateInput,
  FeedTestResult,
  Digest,
  DigestListResponse,
  OverviewMetrics,
  PipelineRun,
} from "./types";

const API_BASE = "/api";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errorJson = await res.json();
      if (errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export async function getOverview(): Promise<OverviewMetrics> {
  const res = await fetch(`${API_BASE}/overview`, { cache: "no-store" });
  return handleResponse<OverviewMetrics>(res);
}

export async function getFeeds(category?: string, isActive?: boolean): Promise<Feed[]> {
  const params = new URLSearchParams();
  if (category) params.append("category", category);
  if (isActive !== undefined) params.append("is_active", String(isActive));
  const res = await fetch(`${API_BASE}/feeds?${params.toString()}`, { cache: "no-store" });
  return handleResponse<Feed[]>(res);
}

export async function createFeed(input: FeedCreateInput): Promise<Feed> {
  const res = await fetch(`${API_BASE}/feeds`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handleResponse<Feed>(res);
}

export async function updateFeed(id: number, input: FeedUpdateInput): Promise<Feed> {
  const res = await fetch(`${API_BASE}/feeds/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handleResponse<Feed>(res);
}

export async function toggleFeed(id: number): Promise<Feed> {
  const res = await fetch(`${API_BASE}/feeds/${id}/toggle`, {
    method: "PATCH",
  });
  return handleResponse<Feed>(res);
}

export async function deleteFeed(id: number): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE}/feeds/${id}`, {
    method: "DELETE",
  });
  return handleResponse<{ status: string; message: string }>(res);
}

export async function testFeedUrl(url: string, limit: number = 3): Promise<FeedTestResult> {
  const res = await fetch(`${API_BASE}/feeds/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, limit }),
  });
  return handleResponse<FeedTestResult>(res);
}

export async function getDigests(page: number = 1, limit: number = 10): Promise<DigestListResponse> {
  const res = await fetch(`${API_BASE}/digests?page=${page}&limit=${limit}`, {
    cache: "no-store",
  });
  return handleResponse<DigestListResponse>(res);
}

export async function getDigest(id: number): Promise<Digest> {
  const res = await fetch(`${API_BASE}/digests/${id}`, { cache: "no-store" });
  return handleResponse<Digest>(res);
}

export async function updateDigest(
  id: number,
  data: { summary_markdown?: string; status?: string }
): Promise<Digest> {
  const res = await fetch(`${API_BASE}/digests/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<Digest>(res);
}

export async function broadcastDigest(id: number): Promise<{
  status: string;
  message: string;
  broadcasted_at: string;
  chunks_sent: number;
}> {
  const res = await fetch(`${API_BASE}/digests/${id}/broadcast`, {
    method: "POST",
  });
  return handleResponse(res);
}

export async function triggerPipelineRun(params: {
  dry_run?: boolean;
  auto_broadcast?: boolean;
}): Promise<{
  status: string;
  run_id: string;
  dry_run: boolean;
  auto_broadcast: boolean;
  message: string;
}> {
  const res = await fetch(`${API_BASE}/pipeline/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return handleResponse(res);
}

export async function getPipelineRuns(limit: number = 15): Promise<PipelineRun[]> {
  const res = await fetch(`${API_BASE}/pipeline/runs?limit=${limit}`, {
    cache: "no-store",
  });
  return handleResponse<PipelineRun[]>(res);
}

export async function getPipelineRun(runId: string): Promise<PipelineRun> {
  const res = await fetch(`${API_BASE}/pipeline/runs/${runId}`, {
    cache: "no-store",
  });
  return handleResponse<PipelineRun>(res);
}
