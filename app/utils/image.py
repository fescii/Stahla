# filepath: app/utils/image.py
"""
Image processing utilities for handling user profile pictures.
Provides functionality to resize images to thumbnails and validate image formats.
"""

import io
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageOps
import logfire


class ImageProcessor:
  """Helper class for processing uploaded images"""

  SUPPORTED_FORMATS = {'JPEG', 'PNG', 'GIF', 'WEBP'}
  THUMBNAIL_SIZE = (150, 150)
  DEFAULT_QUALITY = 85

  @staticmethod
  def validate_image(file_content: bytes) -> bool:
    """
    Validate if the file content is a valid image.

    Args:
        file_content: Raw bytes of the uploaded file

    Returns:
        bool: True if valid image, False otherwise
    """
    try:
      with Image.open(io.BytesIO(file_content)) as img:
        # Verify it's a valid image by attempting to load it
        img.verify()
        return img.format in ImageProcessor.SUPPORTED_FORMATS
    except Exception as e:
      logfire.warning(f"Image validation failed: {e}")
      return False

  @staticmethod
  def get_image_format(file_content: bytes) -> Optional[str]:
    """
    Get the format of the image from file content.

    Args:
        file_content: Raw bytes of the uploaded file

    Returns:
        str: Image format (e.g., 'JPEG', 'PNG') or None if invalid
    """
    try:
      with Image.open(io.BytesIO(file_content)) as img:
        return img.format
    except Exception:
      return None

  @staticmethod
  def create_thumbnail(
      file_content: bytes,
      size: Optional[Tuple[int, int]] = None,
      quality: Optional[int] = None
  ) -> bytes:
    """
    Create a thumbnail from image file content.

    Args:
        file_content: Raw bytes of the uploaded image
        size: Tuple of (width, height) for thumbnail. Defaults to (100, 100)
        quality: JPEG quality (1-100). Defaults to 85

    Returns:
        bytes: Processed thumbnail image as bytes

    Raises:
        ValueError: If the image cannot be processed
    """
    if size is None:
      size = ImageProcessor.THUMBNAIL_SIZE
    if quality is None:
      quality = ImageProcessor.DEFAULT_QUALITY

    try:
      # Open the image
      with Image.open(io.BytesIO(file_content)) as img:
        # Convert to RGB if necessary (for JPEG output)
        if img.mode in ('RGBA', 'LA', 'P'):
          # Create a white background for transparent images
          background = Image.new('RGB', img.size, (255, 255, 255))
          if img.mode == 'P':
            img = img.convert('RGBA')
          background.paste(img, mask=img.split()
                           [-1] if img.mode == 'RGBA' else None)
          img = background
        elif img.mode != 'RGB':
          img = img.convert('RGB')

        # Auto-orient the image based on EXIF data
        img = ImageOps.exif_transpose(img)

        # Create thumbnail that fills the entire area without whitespace
        # Calculate dimensions to crop to square first
        width, height = img.size
        min_dimension = min(width, height)

        # Calculate crop box to get center square
        left = (width - min_dimension) // 2
        top = (height - min_dimension) // 2
        right = left + min_dimension
        bottom = top + min_dimension

        # Crop to square
        img = img.crop((left, top, right, bottom))

        # Resize to exact target size
        img = img.resize(size, Image.Resampling.LANCZOS)

        # Save to bytes
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()

    except Exception as e:
      logfire.error(f"Error creating thumbnail: {e}", exc_info=True)
      raise ValueError(f"Failed to process image: {str(e)}")

  @staticmethod
  def get_file_extension_for_format(image_format: str) -> str:
    """
    Get the appropriate file extension for an image format.

    Args:
        image_format: Image format (e.g., 'JPEG', 'PNG')

    Returns:
        str: File extension (e.g., '.jpg', '.png')
    """
    format_to_ext = {
        'JPEG': '.jpg',
        'PNG': '.png',
        'GIF': '.gif',
        'WEBP': '.webp'
    }
    return format_to_ext.get(image_format, '.jpg')

  @staticmethod
  def process_user_picture(
      file_content: bytes,
      original_filename: str,
      user_id: str,
      timestamp: str
  ) -> Tuple[bytes, str]:
    """
    Process a user's profile picture upload.

    Args:
        file_content: Raw bytes of the uploaded image
        original_filename: Original filename from upload
        user_id: User ID for filename generation
        timestamp: Timestamp for filename generation

    Returns:
        Tuple[bytes, str]: Processed image bytes and final filename

    Raises:
        ValueError: If the image cannot be processed
    """
    # Validate the image
    if not ImageProcessor.validate_image(file_content):
      raise ValueError("Invalid image format or corrupted image data")

    # Create thumbnail
    thumbnail_bytes = ImageProcessor.create_thumbnail(file_content)

    # Generate filename - always use .jpg for thumbnails since we convert to JPEG
    original_name = Path(original_filename).stem
    final_filename = f"{original_name}_{timestamp}.jpg"

    logfire.info(
        f"Processed user picture: {original_filename} -> {final_filename}")

    return thumbnail_bytes, final_filename


# Convenience functions for backward compatibility
def create_thumbnail(file_content: bytes, size: Tuple[int, int] = (150, 150)) -> bytes:
  """Create a thumbnail from image file content."""
  return ImageProcessor.create_thumbnail(file_content, size)


def validate_image(file_content: bytes) -> bool:
  """Validate if the file content is a valid image."""
  return ImageProcessor.validate_image(file_content)


def process_user_picture(
    file_content: bytes,
    original_filename: str,
    user_id: str,
    timestamp: str
) -> Tuple[bytes, str]:
  """Process a user's profile picture upload."""
  return ImageProcessor.process_user_picture(file_content, original_filename, user_id, timestamp)
