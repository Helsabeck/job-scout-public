"""
digest.py - Build and send the weekly HTML email digest.
Uses Gmail SMTP with an app password (stored in GitHub Secrets).
"""

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def build_html(
    matched_jobs: list[dict],
    failed_companies: list[str],
    run_date: str,
    is_first_run: bool = False,
    stats: dict = None,
) -> str:
    """Build the HTML email body."""

    if is_first_run:
        return f"""
        <html><body style="font-family:-apple-system,Arial,sans-serif;max-width:700px;margin:0 auto;padding:24px;color:#222;">
        <h2 style="color:#1a1a2e;">✅ Job Scout Initialized — {run_date}</h2>
        <p>The job scout is running. All current job IDs have been saved as a baseline.</p>
        <p>From next Monday onward, you'll receive a digest of <strong>new</strong> postings only.</p>
        </body></html>
        """

    # Group matched jobs by company
    by_company: dict[str, list] = {}
    for job in matched_jobs:
        company = job.get("company", "Unknown")
        by_company.setdefault(company, []).append(job)

    # Build job rows
    job_rows = ""
    for company in sorted(by_company.keys()):
        jobs = by_company[company]
        job_rows += f"""
        <tr>
            <td colspan="3" style="background:#1a1a2e;color:#fff;padding:9px 14px;
                font-weight:600;font-size:13px;letter-spacing:0.3px;">
                {company}&nbsp;&nbsp;<span style="font-weight:normal;opacity:0.75;">
                ({len(jobs)} new match{"es" if len(jobs) != 1 else ""})</span>
            </td>
        </tr>"""
        for job in jobs:
            location = job.get("location", "") or "—"
            reason = job.get("fit_reason", "")
            job_rows += f"""
        <tr style="border-bottom:1px solid #eee;">
            <td style="padding:10px 14px;vertical-align:top;min-width:220px;">
                <a href="{job.get('url', '#')}" target="_blank"
                   style="color:#0055cc;font-weight:600;text-decoration:none;font-size:14px;">
                    {job.get('title', 'Untitled')}
                </a>
            </td>
            <td style="padding:10px 14px;color:#555;font-size:13px;
                vertical-align:top;white-space:nowrap;">
                {location}
            </td>
            <td style="padding:10px 14px;color:#444;font-size:13px;
                vertical-align:top;font-style:italic;">
                {reason}
            </td>
        </tr>"""

    # Stats summary table
    stats_section = ""
    if stats and not is_first_run:
        matched_color = "#2d7a2d" if stats.get("matched", 0) > 0 else "#888"
        stats_section = f"""
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;
            font-size:13px;color:#555;border:1px solid #eee;border-radius:6px;">
            <tr style="background:#f9f9f9;">
                <td style="padding:8px 14px;">📥 Total jobs fetched</td>
                <td style="padding:8px 14px;text-align:right;font-weight:600;">
                    {stats.get("fetched", 0):,}
                </td>
            </tr>
            <tr>
                <td style="padding:8px 14px;">🆕 New since last run</td>
                <td style="padding:8px 14px;text-align:right;font-weight:600;">
                    {stats.get("new", 0):,}
                </td>
            </tr>
            <tr style="background:#f9f9f9;">
                <td style="padding:8px 14px;">🔑 Passed keyword filter</td>
                <td style="padding:8px 14px;text-align:right;font-weight:600;">
                    {stats.get("candidates", 0):,}
                </td>
            </tr>
            <tr>
                <td style="padding:8px 14px;">✅ Matched by Claude</td>
                <td style="padding:8px 14px;text-align:right;font-weight:600;color:{matched_color};">
                    {stats.get("matched", 0):,}
                </td>
            </tr>
        </table>"""

    # Warning section for failed companies
    warning_section = ""
    if failed_companies:
        warning_section = f"""
        <p style="margin-top:24px;padding:12px 16px;background:#fff8e1;
            border-left:4px solid #f59e0b;font-size:13px;color:#555;">
            ⚠️ <strong>Could not reach:</strong> {", ".join(failed_companies)}.
            These sites may block automated requests. Check their career pages manually.
        </p>"""

    no_matches_msg = ""
    if not matched_jobs:
        no_matches_msg = """
        <p style="padding:20px;background:#f9f9f9;border-radius:6px;color:#666;text-align:center;">
            No new matching roles found this week. The search continues.
        </p>"""

    table_section = ""
    if matched_jobs:
        table_section = f"""
        <table style="width:100%;border-collapse:collapse;
            border:1px solid #ddd;border-radius:6px;overflow:hidden;font-size:14px;">
            <thead>
                <tr style="background:#f5f5f5;">
                    <th style="text-align:left;padding:10px 14px;color:#333;">Role</th>
                    <th style="text-align:left;padding:10px 14px;color:#333;">Location</th>
                    <th style="text-align:left;padding:10px 14px;color:#333;">Why It Fits</th>
                </tr>
            </thead>
            <tbody>{job_rows}</tbody>
        </table>"""

    count_text = (
        f"<strong>{len(matched_jobs)} new match{'es' if len(matched_jobs) != 1 else ''}</strong>"
        f" across {len(by_company)} company/companies."
        if matched_jobs
        else "No new matches this week."
    )

    return f"""
    <html>
    <body style="font-family:-apple-system,Arial,sans-serif;max-width:700px;
        margin:0 auto;padding:24px;color:#222;">

        <h2 style="color:#1a1a2e;margin-bottom:4px;">
            🔍 Job Scout — {run_date}
        </h2>
        <p style="color:#666;margin-top:4px;margin-bottom:20px;font-size:14px;">
            {count_text}
        </p>

        {stats_section}
        {table_section}
        {no_matches_msg}
        {warning_section}

        <p style="color:#aaa;font-size:11px;margin-top:32px;border-top:1px solid #eee;padding-top:12px;">
            Generated {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")} by Job Scout.
            To add or remove companies, edit companies.yaml in your repo.
        </p>
    </body>
    </html>
    """


def send_email(html: str, matched_count: int, is_first_run: bool = False) -> None:
    """Send the digest via Gmail SMTP."""
    sender = os.environ["EMAIL_SENDER"]
    recipient = os.environ["EMAIL_RECIPIENT"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]

    if is_first_run:
        subject = "✅ Job Scout: Initialized and running"
    elif matched_count > 0:
        subject = f"🔍 Job Scout: {matched_count} new role{'s' if matched_count != 1 else ''} found"
    else:
        subject = "Job Scout: No new matches this week"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, app_password)
            server.sendmail(sender, recipient, msg.as_string())
        print(f"  [Digest] Email sent → {recipient} | Subject: {subject}")
    except smtplib.SMTPAuthenticationError:
        print("  [Digest] Auth failed — check GMAIL_APP_PASSWORD secret.")
        raise
    except Exception as e:
        print(f"  [Digest] Failed to send email: {e}")
        raise
