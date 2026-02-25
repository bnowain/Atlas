import { apiFetch } from './client'

export interface MeetingDetail {
  meeting_id: string
  title: string
  governing_body: string
  meeting_type: string
  meeting_date: string | null
  category: string
  governing_body_id: string | null
  description: string | null
  source_url: string | null
  page_url: string | null
  thumbnail_url: string | null
  video_url: string | null
  agenda_url: string | null
  minutes_url: string | null
  packet_url: string | null
  media_directory: string | null
  processed_at: string | null
  created_at: string
  summary_short: string | null
  summary_long: string | null
  summary_updated_at: string | null
}

export interface SegmentAssignment {
  assignment_id: string
  segment_id: string
  predicted_person_id: string | null
  similarity_score: number | null
  verified: boolean
  tagged: boolean
}

export interface TranscriptSegment {
  segment_id: string
  meeting_id: string
  start_time: number
  end_time: number
  text: string
  raw_speaker_label: string | null
  source_type: string
  assignment: SegmentAssignment | null
}

export interface VoteMember {
  name: string
  vote: string
}

export interface VoteRecord {
  vote_id: string
  meeting_id: string
  document_id: string | null
  meeting_date: string | null
  governing_body: string | null
  agenda_section: string | null
  item_description: string | null
  resolution_number: string | null
  outcome: string | null
  vote_tally: string | null
  mover: string | null
  seconder: string | null
  members: VoteMember[]
}

export interface MediaFile {
  media_id: string
  meeting_id: string
  file_type: string
  file_path: string
  duration: number | null
  transcode_status: string | null
}

export interface PersonSummary {
  person_id: string
  canonical_name: string
  voiceprint_count: number
}

export async function getMeeting(id: string): Promise<MeetingDetail | null> {
  try {
    return await apiFetch<MeetingDetail>(`/spokes/civic_media/api/meetings/${id}`)
  } catch {
    return null
  }
}

export async function getSegments(id: string): Promise<TranscriptSegment[]> {
  try {
    return await apiFetch<TranscriptSegment[]>(`/spokes/civic_media/api/segments/${id}`)
  } catch {
    return []
  }
}

export async function getVotes(id: string): Promise<VoteRecord[]> {
  try {
    return await apiFetch<VoteRecord[]>(`/spokes/civic_media/api/votes/${id}`)
  } catch {
    return []
  }
}

export async function getMediaFiles(id: string): Promise<MediaFile[]> {
  try {
    return await apiFetch<MediaFile[]>(`/spokes/civic_media/api/media/${id}`)
  } catch {
    return []
  }
}

export async function getPeople(): Promise<PersonSummary[]> {
  try {
    return await apiFetch<PersonSummary[]>(`/spokes/civic_media/api/people/`)
  } catch {
    return []
  }
}

/** Returns the Atlas proxy URL for streaming a meeting's media file. */
export function mediaStreamUrl(meetingId: string): string {
  return `/api/spokes/civic_media/media/${meetingId}/video`
}
