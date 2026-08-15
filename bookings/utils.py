import io
import qrcode
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

def generate_qr_code_image(data_string):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(data_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer)
    buffer.seek(0)
    return buffer

def generate_ticket_pdf(booking):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#0f172a'),
        alignment=1, # Center
        spaceAfter=12
    )

    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#d97706'),
        alignment=1,
        spaceAfter=15
    )

    label_style = ParagraphStyle(
        'LabelStyle',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#64748b'),
        fontName='Helvetica-Bold'
    )

    value_style = ParagraphStyle(
        'ValueStyle',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0f172a'),
        fontName='Helvetica'
    )

    # Document Header
    story.append(Paragraph("CINEMA MOVIE BOOKING TICKET", title_style))
    story.append(Paragraph(f"Ref: {booking.booking_reference}", header_style))
    story.append(Spacer(1, 10))

    # Generate QR code
    qr_buffer = generate_qr_code_image(f"BOOKING_REF:{booking.booking_reference}|USER:{booking.user.username}")
    qr_image = Image(qr_buffer, width=120, height=120)

    # Seat Labels list
    seats_str = ", ".join([bs.seat.label for bs in booking.booked_seats.all()])

    ticket_data = [
        [Paragraph("Movie:", label_style), Paragraph(booking.show.movie.title, value_style)],
        [Paragraph("Theater:", label_style), Paragraph(booking.show.theater.name, value_style)],
        [Paragraph("Screen:", label_style), Paragraph(f"{booking.show.screen.name} ({booking.show.screen.screen_type})", value_style)],
        [Paragraph("Show Date:", label_style), Paragraph(str(booking.show.show_date), value_style)],
        [Paragraph("Show Time:", label_style), Paragraph(f"{booking.show.start_time.strftime('%H:%M')} - {booking.show.end_time.strftime('%H:%M')}", value_style)],
        [Paragraph("Seats:", label_style), Paragraph(seats_str, value_style)],
        [Paragraph("Passenger / User:", label_style), Paragraph(booking.user.get_full_name() or booking.user.username, value_style)],
        [Paragraph("Total Paid:", label_style), Paragraph(f"${booking.total_amount}", value_style)],
        [Paragraph("Payment Status:", label_style), Paragraph(booking.payment_status, value_style)],
    ]

    details_table = Table(ticket_data, colWidths=[120, 220])
    details_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))

    # Layout with QR on the right
    main_table = Table([[details_table, qr_image]], colWidths=[360, 150])
    main_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
    ]))

    story.append(main_table)
    story.append(Spacer(1, 30))
    story.append(Paragraph("Please present this digital ticket or QR code at the theater entrance.", label_style))

    doc.build(story)
    buffer.seek(0)
    return buffer
