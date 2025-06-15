import json
from mitlesen.pipeline.base import PipelineStep, PipelineContext
from mitlesen.logger import logger
from mitlesen.db import Database, Video

class UploadStep(PipelineStep):
    def execute(self, context: PipelineContext) -> bool:
        logger.info(f"💾 Starting upload for {context.youtube_id}")
        try:
            db = Database()
            if Video.exists(db.client, context.youtube_id):
                logger.info(f"Video {context.youtube_id} already exists in database")
                return self.run_next(context)
            with open(context.augmented_transcript_path, 'r', encoding='utf-8') as file:
                transcript = json.load(file)
            Video.insert(
                client=db.client,
                title=context.title,
                youtube_id=context.youtube_id,
                is_premium=context.is_premium,
                language=context.language,
                transcript=json.dumps(transcript)
            )
            logger.info(f"✅ Upload completed for {context.youtube_id}")
            return self.run_next(context)
        except Exception as e:
            logger.error(f"❌ Upload failed: {str(e)}")
            return False
        finally:
            try:
                db.close()
            except Exception:
                pass 