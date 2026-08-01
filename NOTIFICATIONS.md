# Optional notifications

The daily, revalidation, and settlement workflows can deliver a short operational summary after the bot has safely saved its state. Delivery failures never cancel bets, change the bankroll, or fail the workflow.

Notifications are disabled by default. Add the relevant values under **GitHub repository settings → Secrets and variables → Actions**.

## Telegram

Add both secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Email (SMTP)

Required secrets:

- `SMTP_HOST`
- `ALERT_EMAIL_FROM`
- `ALERT_EMAIL_TO`

Optional secrets:

- `SMTP_PORT` (defaults to `465` for SSL or `587` otherwise)
- `SMTP_USERNAME` and `SMTP_PASSWORD` (configure both or neither)
- `SMTP_USE_SSL` (`true` or `false`; default `false`)
- `SMTP_STARTTLS` (`true` or `false`; default `true` when SSL is disabled)

The bot writes only the channel, delivery status, and sanitized error class to `notification-delivery.json`. Tokens, passwords, chat IDs, email addresses, and server responses are never stored there or printed in failure logs.
