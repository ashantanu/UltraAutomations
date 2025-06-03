from typing import Optional
from pathlib import Path
from moviepy.editor import ImageClip, AudioFileClip, CompositeAudioClip
from app.utils.logging_utils import get_logger
from app.video.models import VideoConfig, AudioConfig, VideoInput, VideoProcessingResult
from app.video.utils import validate_paths_and_permissions, get_ffmpeg_params

logger = get_logger(__name__)

class VideoProcessor:
    """Handles video processing operations."""
    
    def __init__(
        self,
        video_config: Optional[VideoConfig] = None,
        audio_config: Optional[AudioConfig] = None
    ):
        self.video_config = video_config or VideoConfig()
        self.audio_config = audio_config or AudioConfig()

    def create_video(self, input_data: VideoInput) -> VideoProcessingResult:
        """
        Create a video from image and audio files.
        
        Args:
            input_data: VideoInput object containing all necessary paths
            
        Returns:
            VideoProcessingResult: Result of the video processing operation
        """
        try:
            # Validate paths and permissions
            paths = {
                'main_audio': input_data.main_audio_path,
                'image': input_data.image_path,
                'output': input_data.output_path,
                'background_music': input_data.background_music_path
            }
            
            is_valid, error_msg = validate_paths_and_permissions(
                paths,
                self.video_config.min_free_space_gb
            )
            if not is_valid:
                return VideoProcessingResult(
                    success=False,
                    message=error_msg,
                    error=error_msg
                )

            logger.info("Loading audio and image clips...")
            main_audio = AudioFileClip(str(input_data.main_audio_path))
            image_clip = ImageClip(str(input_data.image_path)).set_duration(main_audio.duration)

            # Handle background music if provided
            if input_data.background_music_path:
                logger.info(f"Loading background music from: {input_data.background_music_path}")
                try:
                    background_music = AudioFileClip(str(input_data.background_music_path))
                    logger.info(f"Background music loaded successfully. Duration: {background_music.duration:.2f}s")
                    
                    # Loop background music if needed
                    if background_music.duration < main_audio.duration:
                        n_loops = int(main_audio.duration / background_music.duration) + 1
                        logger.info(f"Background music duration ({background_music.duration:.2f}s) is shorter than main audio ({main_audio.duration:.2f}s). Looping {n_loops} times.")
                        background_music_clips = [background_music] * n_loops
                        background_music = CompositeAudioClip(background_music_clips)
                        background_music = background_music.subclip(0, main_audio.duration)
                        logger.info(f"Background music looped to match main audio duration: {background_music.duration:.2f}s")

                    # Adjust volumes and create composite audio
                    logger.info(f"Adjusting audio volumes - Main: {self.audio_config.main_audio_volume}x, Background: {self.audio_config.background_music_volume}x")
                    main_audio = main_audio.volumex(self.audio_config.main_audio_volume)
                    background_music = background_music.volumex(self.audio_config.background_music_volume)
                    final_audio = CompositeAudioClip([main_audio, background_music])
                    logger.info("Composite audio created successfully with background music")
                except Exception as e:
                    logger.error(f"Error processing background music: {str(e)}", exc_info=True)
                    logger.warning("Falling back to main audio only")
                    final_audio = main_audio.volumex(self.audio_config.main_audio_volume)
            else:
                logger.info("No background music provided, using main audio only")
                final_audio = main_audio.volumex(self.audio_config.main_audio_volume)

            # Set audio to image clip
            image_clip = image_clip.set_audio(final_audio)

            logger.info("Writing video file...")
            image_clip.write_videofile(
                str(input_data.output_path),
                fps=self.video_config.fps,
                codec='libx264',
                audio_codec='aac',
                preset=self.video_config.preset,
                threads=self.video_config.threads,
                bitrate=self.video_config.video_bitrate,
                audio_bitrate=self.video_config.audio_bitrate,
                verbose=True,
                logger=None,
                ffmpeg_params=get_ffmpeg_params()
            )

            # Clean up
            main_audio.close()
            if input_data.background_music_path:
                background_music.close()
            image_clip.close()

            return VideoProcessingResult(
                success=True,
                message=f"Video successfully created at: {input_data.output_path}",
                output_path=input_data.output_path
            )

        except Exception as e:
            error_msg = f"Error creating video: {str(e)}"
            logger.error(error_msg)
            return VideoProcessingResult(
                success=False,
                message=error_msg,
                error=str(e)
            ) 