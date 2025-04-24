from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import datetime


class YouTubeTranscriptFetcher:
    """Fetch and manage YouTube video transcripts (with timestamps)."""
    def __init__(
        self,
        language_code: str = 'en',
        preserve_formatting: bool = False
    ):
        # Instantiate the API client
        self.api = YouTubeTranscriptApi()
        self.language_code = language_code
        self.preserve_formatting = preserve_formatting

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Convert seconds to HH:MM:SS format."""
        return str(datetime.timedelta(seconds=int(seconds)))

    def fetch(self, video_id: str) -> str:
        """
        Fetches the transcript for the given YouTube video ID in the manager's language.
        Returns:
            A single string with one “[HH:MM:SS] text” entry per line.
        Raises:
            ValueError: if no transcript is available.
        """
        try:
            transcript = self.api.fetch(
                video_id,
                languages=[self.language_code],
                preserve_formatting=self.preserve_formatting
            )
        except TranscriptsDisabled:
            raise ValueError("Transcripts are disabled for this video.")
        except NoTranscriptFound:
            raise ValueError(f"No transcript found for language '{self.language_code}'.")
        except Exception as e:
            raise ValueError(f"Unexpected error fetching transcript: {e!s}")

        lines = []
        for snippet in transcript:
            ts = self._format_timestamp(snippet.start)
            lines.append(f"[{ts}] {snippet.text}")

        return "\n".join(lines)


if __name__ == "__main__":
    yt = YouTubeTranscriptFetcher(language_code='de', preserve_formatting=True)
    vid = 't0SQPbD2F08'
    try:
        print(yt.fetch(vid))
    except ValueError as err:
        print(f"❌ {err}")
