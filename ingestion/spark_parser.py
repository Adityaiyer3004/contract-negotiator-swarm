import io
import logging
from typing import Optional

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    PdfReader = None  # type: ignore
    HAS_PYPDF = False

try:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import udf
    from pyspark.sql.types import StringType
    HAS_PYSPARK = True
except ImportError:
    SparkSession = None  # type: ignore
    udf = None  # type: ignore
    StringType = None  # type: ignore
    HAS_PYSPARK = False


logger = logging.getLogger(__name__)

# Global SparkSession cache
_spark_session: Optional[SparkSession] = None


def get_spark_session() -> SparkSession:
    """Get or create a local PySpark session for contract processing."""
    global _spark_session
    if _spark_session is None or _spark_session._sc._is_closed:  # type: ignore
        _spark_session = (
            SparkSession.builder.appName("ContractPDFIngestion")
            .master("local[*]")
            .config("spark.driver.bindAddress", "127.0.0.1")
            .config("spark.ui.enabled", "false")
            .getOrCreate()
        )
        _spark_session.sparkContext.setLogLevel("ERROR")
    return _spark_session


def extract_pdf_bytes(content_bytes: bytes) -> str:
    """Extract raw text from PDF bytes using PyPDF."""
    if not content_bytes:
        return ""
    try:
        pdf_file = io.BytesIO(content_bytes)
        reader = PdfReader(pdf_file)
        text_pages = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text_pages.append(extracted)
        return "\n".join(text_pages).strip()
    except Exception as e:
        logger.error(f"Error parsing PDF bytes with pypdf: {e}")
        return f"Error extracting PDF text: {str(e)}"


class PySparkIngestor:
    """In-memory PySpark PDF Ingestion Engine."""

    def __init__(self):
        self._spark = None

    @property
    def spark(self) -> Optional[SparkSession]:
        if HAS_PYSPARK and (self._spark is None or self._spark._sc._is_closed):  # type: ignore
            try:
                self._spark = get_spark_session()
            except Exception as e:
                logger.warning(
                    f"Could not initialize PySpark session ({e}), using direct extraction fallback."
                )
                self._spark = None
        return self._spark

    def process_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """Processes a raw byte stream directly into PySpark without saving to disk."""
        if not pdf_bytes:
            return ""

        if not HAS_PYSPARK or not self.spark:
            logger.info(
                "PySpark not initialized in environment, using direct text extraction fallback."
            )
            return extract_pdf_bytes(pdf_bytes)

        try:
            # Spark cannot easily read raw bytes directly from memory without RDD mapping
            # So we create a quick single-row DataFrame with the binary payload
            df = self.spark.createDataFrame([(pdf_bytes,)], ["content"])

            # Register PySpark UDF
            parse_udf = udf(extract_pdf_bytes, StringType())

            # Process in Spark DataFrame
            processed_df = df.withColumn("parsed_text", parse_udf("content"))

            # Collect result
            result = processed_df.select("parsed_text").collect()
            return result[0]["parsed_text"] if result and len(result) > 0 else ""
        except Exception as e:
            logger.warning(
                f"PySpark processing error, falling back to direct extraction: {e}"
            )
            return extract_pdf_bytes(pdf_bytes)


# Singleton ingestor instance
ingestor = PySparkIngestor()


def parse_pdf_contract_spark(pdf_bytes: bytes) -> str:
    """Ingest binary PDF content using PySpark UDF and extract clean raw text."""
    return ingestor.process_pdf_bytes(pdf_bytes)


if __name__ == "__main__":
    print("PySpark in-memory ingestor module initialized successfully.")
