import React, { useRef, useState, useEffect, useCallback } from 'react';
import '../../assets/styles/VideoPlayerPanel.css';

interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
}

/** A fine-grained caption (sentence-level) derived from the 30s chunks */
interface CaptionSegment {
  start: number;
  end: number;
  text: string;
}

interface VideoPlayerPanelProps {
  videoUrl: string;
  transcriptRaw: string;
  /** When this value changes, the video seeks to this time (seconds) */
  seekTime?: number | null;
}

/** Parse "00:01:30" → seconds */
function parseTimestamp(ts: string): number {
  const parts = ts.trim().split(':');
  if (parts.length === 3) return parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseInt(parts[2]);
  if (parts.length === 2) return parseInt(parts[0]) * 60 + parseInt(parts[1]);
  return parseFloat(ts);
}

/** Parse raw transcript "[HH:MM:SS --> HH:MM:SS] text..." into segments */
function parseTranscript(raw: string): TranscriptSegment[] {
  if (!raw) return [];
  const segments: TranscriptSegment[] = [];
  const regex = /\[(\d{2}:\d{2}:\d{2})\s*-->\s*(\d{2}:\d{2}:\d{2})\]\s*([\s\S]*?)(?=\n\s*\[|\s*$)/g;
  let match;
  while ((match = regex.exec(raw)) !== null) {
    const start = parseTimestamp(match[1]);
    const end = parseTimestamp(match[2]);
    const text = match[3].trim();
    if (text) segments.push({ start, end, text });
  }
  return segments;
}

/**
 * Split a long text into sentence-level chunks for movie-style captions.
 * Aims for ~60-80 character lines, splitting on sentence boundaries first,
 * then on commas for very long sentences.
 */
function splitIntoSentences(text: string): string[] {
  // Split on sentence-ending punctuation
  const rawSentences = text.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [text];
  const result: string[] = [];

  for (const sentence of rawSentences) {
    const trimmed = sentence.trim();
    if (!trimmed) continue;

    if (trimmed.length > 90) {
      // Split long sentences at commas
      const parts = trimmed.split(/,\s*/);
      let current = '';
      for (const part of parts) {
        if (current.length + part.length > 70 && current) {
          result.push(current.trim());
          current = part;
        } else {
          current += (current ? ', ' : '') + part;
        }
      }
      if (current.trim()) result.push(current.trim());
    } else {
      result.push(trimmed);
    }
  }

  return result.filter(s => s.length > 0);
}

/**
 * Convert 30-second transcript segments into fine-grained, sentence-level
 * caption segments with proportional timing — like real movie subtitles.
 */
function createCaptions(segments: TranscriptSegment[]): CaptionSegment[] {
  const captions: CaptionSegment[] = [];

  for (const segment of segments) {
    const sentences = splitIntoSentences(segment.text);
    const duration = segment.end - segment.start;
    const timePerSentence = duration / sentences.length;

    sentences.forEach((sentence, i) => {
      captions.push({
        start: segment.start + i * timePerSentence,
        end: segment.start + (i + 1) * timePerSentence,
        text: sentence,
      });
    });
  }

  return captions;
}

const VideoPlayerPanel: React.FC<VideoPlayerPanelProps> = ({ videoUrl, transcriptRaw, seekTime }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentCaption, setCurrentCaption] = useState('');
  const [captions] = useState<CaptionSegment[]>(() => {
    const segments = parseTranscript(transcriptRaw);
    return createCaptions(segments);
  });

  // Seek when external seekTime prop changes
  useEffect(() => {
    if (seekTime != null && videoRef.current) {
      videoRef.current.currentTime = seekTime;
      videoRef.current.play().catch(() => {});
    }
  }, [seekTime]);

  // Update current caption based on video time
  const handleTimeUpdate = useCallback(() => {
    if (!videoRef.current) return;
    const t = videoRef.current.currentTime;

    // Binary-style search through captions
    let caption = '';
    for (let i = 0; i < captions.length; i++) {
      if (t >= captions[i].start && t < captions[i].end) {
        caption = captions[i].text;
        break;
      }
    }
    setCurrentCaption(caption);
  }, [captions]);

  return (
    <div className="vp-container">
      <div className="vp-video-wrapper">
        <video
          ref={videoRef}
          src={videoUrl}
          onTimeUpdate={handleTimeUpdate}
          controls
          controlsList="nofullscreen nodownload"
          disablePictureInPicture
          className="vp-video"
          preload="metadata"
        />
        {/* Movie-style caption overlay */}
        {currentCaption && (
          <div className="vp-caption-overlay" key={currentCaption}>
            <span className="vp-caption-text">{currentCaption}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoPlayerPanel;
