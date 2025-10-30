from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_report(video_metadata: Dict[str, Any], output_path: Path) -> Path:
    doc = SimpleDocTemplate(str(output_path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    title = f"Facial Recognition Report - {video_metadata.get('filename', 'Video')}"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 12))

    summary_data = [
        ["Generated At", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")],
        ["Video ID", video_metadata.get("video_id", "")],
        ["Unique People", video_metadata["summary"].get("unique_people", 0)],
        ["Total Face Appearances", video_metadata["summary"].get("total_faces", 0)],
    ]
    summary_table = Table(summary_data, hAlign="LEFT")
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 24))

    story.append(Paragraph("Per Person Summary", styles["Heading2"]))
    story.append(Spacer(1, 12))

    per_person = video_metadata["summary"].get("per_person", [])
    for person in per_person:
        header = f"{person['name']} (ID: {person['person_id']}) - {person['appearances']} appearances"
        story.append(Paragraph(header, styles["Heading3"]))
        story.append(Spacer(1, 6))

        detail_rows = [["Timestamp (s)", "Frame Index", "Bounding Box (top, right, bottom, left)"]]
        for detail in person.get("details", []):
            bbox = ", ".join(str(v) for v in detail.get("bounding_box", []))
            detail_rows.append([str(detail.get("timestamp", "")), str(detail.get("frame_index", "")), bbox])

        table = Table(detail_rows, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0E0E0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.darkgrey),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 12))

    doc.build(story)
    return output_path
