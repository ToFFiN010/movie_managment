import os
import uuid
import qrcode
import logging
from datetime import datetime
from io import BytesIO

from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from bookings.models import Booking, Ticket, Payment

logger = logging.getLogger(__name__)


class TicketService:

    @staticmethod
    def generate_qr_code(qr_token, domain="http://localhost:8000"):
        """
        Generates a PNG QR code containing the secure ticket verification URL.
        Saves the QR code into MEDIA_ROOT/tickets/qr/YYYY/MM/ and returns relative path.
        """
        verify_url = f"{domain.rstrip('/')}/tickets/verify/{qr_token}/"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(verify_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF")

        now = timezone.now()
        rel_dir = os.path.join('tickets', 'qr', now.strftime('%Y'), now.strftime('%m'))
        abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)

        filename = f"{qr_token}.png"
        abs_path = os.path.join(abs_dir, filename)
        img.save(abs_path)

        return os.path.join(rel_dir, filename).replace('\\', '/')

    @staticmethod
    def generate_pdf_ticket(booking, domain="http://localhost:8000"):
        """
        Idempotent PDF ticket generator for a confirmed booking using ReportLab.
        Returns the Ticket model instance.
        """
        # Idempotency Check: Return existing ticket if already generated
        ticket, created = Ticket.objects.get_or_create(booking=booking)
        if not created and ticket.pdf_file and os.path.exists(ticket.pdf_file.path):
            logger.info(f"Ticket PDF already exists for booking {booking.booking_reference}")
            return ticket

        # Generate QR Code
        qr_rel_path = TicketService.generate_qr_code(ticket.qr_token, domain=domain)
        qr_abs_path = os.path.join(settings.MEDIA_ROOT, qr_rel_path)
        ticket.qr_code_image = qr_rel_path

        # Setup PDF File Storage Path
        now = timezone.now()
        rel_pdf_dir = os.path.join('tickets', now.strftime('%Y'), now.strftime('%m'))
        abs_pdf_dir = os.path.join(settings.MEDIA_ROOT, rel_pdf_dir)
        os.makedirs(abs_pdf_dir, exist_ok=True)

        filename = f"{ticket.ticket_number}.pdf"
        abs_pdf_path = os.path.join(abs_pdf_dir, filename)

        # Build ReportLab Document
        doc = SimpleDocTemplate(
            abs_pdf_path,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        
        # Custom ReportLab Paragraph Styles
        brand_title_style = ParagraphStyle(
            'BrandTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#FFB000'),
            alignment=0
        )

        header_sub_style = ParagraphStyle(
            'HeaderSub',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#94A3B8'),
            alignment=0
        )

        section_heading = ParagraphStyle(
            'SectionHead',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#8B5CF6')
        )

        movie_title_style = ParagraphStyle(
            'MovieTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#0F172A')
        )

        label_style = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#64748B')
        )

        val_style = ParagraphStyle(
            'Val',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=13,
            textColor=colors.HexColor('#1E293B')
        )

        val_bold_style = ParagraphStyle(
            'ValBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#0F172A')
        )

        elements = []

        # 1. Header Banner Box
        banner_data = [
            [
                Paragraph("<b>CINE PRIME CINEMAS</b>", brand_title_style),
                Paragraph(f"<b>OFFICIAL E-TICKET</b><br/><font color='#64748B' size=8>Ticket: {ticket.ticket_number}</font>", header_sub_style)
            ]
        ]
        banner_table = Table(banner_data, colWidths=[340, 200])
        banner_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0F172A')),
            ('PADDING', (0, 0), (-1, -1), 14),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(banner_table)
        elements.append(Spacer(1, 14))

        # 2. Movie & Show Info Card
        show = booking.show
        movie = show.movie
        theater = show.theater
        screen = show.screen

        # Poster Image handling
        poster_elem = None
        if movie.poster and os.path.exists(movie.poster.path):
            try:
                poster_elem = RLImage(movie.poster.path, width=1.3*inch, height=1.95*inch)
            except Exception:
                poster_elem = Paragraph("<b>[POSTER]</b>", val_style)
        else:
            poster_elem = Paragraph("<b>CINEPRIME<br/>CINEMAS</b>", label_style)

        movie_details_data = [
            [Paragraph(f"{movie.title.upper()}", movie_title_style)],
            [Paragraph(f"<b>Genre:</b> {', '.join([g.name for g in movie.genres.all()[:2]]) or 'Cinema'} | <b>Duration:</b> {movie.duration_minutes} mins | <b>Rating:</b> ⭐ {movie.average_rating}", val_style)],
            [Spacer(1, 6)],
            [Paragraph("<b>THEATER & SHOW DETAILS</b>", section_heading)],
            [Paragraph(f"<b>{theater.name}</b> — {screen.name} ({screen.screen_type})", val_bold_style)],
            [Paragraph(f"{theater.address}, {theater.city}", val_style)],
            [Paragraph(f"<b>Date:</b> {show.show_date.strftime('%A, %B %d, %Y')} | <b>Time:</b> {show.start_time.strftime('%I:%M %p')}", val_bold_style)],
        ]
        movie_details_table = Table(movie_details_data, colWidths=[380])
        movie_details_table.setStyle(TableStyle([
            ('PADDING', (0, 0), (-1, -1), 2),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        main_info_table = Table([[poster_elem, movie_details_table]], colWidths=[110, 430])
        main_info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(main_info_table)
        elements.append(Spacer(1, 14))

        # 3. Booking, Seat & Payment Details Table
        booked_seats = booking.booked_seats.select_related('seat')
        seat_labels = ", ".join([bs.seat.label for bs in booked_seats]) or "N/A"
        payment = booking.payment

        summary_data = [
            [
                Paragraph("BOOKED SEATS", label_style),
                Paragraph("TOTAL SEATS", label_style),
                Paragraph("BOOKING REF", label_style),
                Paragraph("TOTAL PAID", label_style)
            ],
            [
                Paragraph(f"<b>{seat_labels}</b>", val_bold_style),
                Paragraph(f"<b>{booked_seats.count()} Ticket(s)</b>", val_style),
                Paragraph(f"<b>{booking.booking_reference}</b>", val_style),
                Paragraph(f"<font color='#059669'><b>₹{booking.total_amount}</b></font>", val_bold_style)
            ],
            [
                Paragraph("PASSENGER / USER", label_style),
                Paragraph("PAYMENT METHOD", label_style),
                Paragraph("TRANSACTION ID", label_style),
                Paragraph("BOOKING STATUS", label_style)
            ],
            [
                Paragraph(f"{booking.user.get_full_name() or booking.user.username}", val_style),
                Paragraph(f"{payment.get_payment_method_display() if payment else 'Razorpay UPI/Card'}", val_style),
                Paragraph(f"{payment.transaction_id or payment.gateway_order_id if payment else 'N/A'}", val_style),
                Paragraph(f"<font color='#8B5CF6'><b>{booking.status}</b></font>", val_bold_style)
            ]
        ]

        summary_table = Table(summary_data, colWidths=[135, 135, 135, 135])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 14))

        # 4. QR Code & Anti-Tamper Security Verification Footer
        qr_img_elem = RLImage(qr_abs_path, width=1.3*inch, height=1.3*inch)
        
        security_text = Paragraph(
            f"<b>SECURITY VERIFICATION & ENTRY RULES</b><br/>"
            f"<font color='#475569' size=8>"
            f"• Please present this QR code at the theater entrance scanner.<br/>"
            f"• Verified Token: <font color='#8B5CF6'><code>{ticket.qr_token[:16]}...</code></font><br/>"
            f"• Verification Portal: <u>http://localhost:8000/tickets/verify/{ticket.qr_token}/</u><br/>"
            f"• Admittance is strictly subject to theater terms. Non-transferable.<br/>"
            f"• Generated on {now.strftime('%b %d, %Y at %I:%M %p')}"
            f"</font>",
            val_style
        )

        verification_table = Table([[qr_img_elem, security_text]], colWidths=[110, 430])
        verification_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFFFFF')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(verification_table)

        # Build PDF
        doc.build(elements)

        # Update Ticket record
        ticket.pdf_file = os.path.join(rel_pdf_dir, filename).replace('\\', '/')
        ticket.save()

        logger.info(f"Successfully generated PDF ticket {ticket.ticket_number} at {abs_pdf_path}")
        return ticket
