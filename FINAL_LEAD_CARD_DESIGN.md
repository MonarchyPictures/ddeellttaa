# Final Lead Card Design

## Overview

The final lead card displays all critical information for instant verification and action.

## Card Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔥 HOT LEAD                                         95/100 [✓ Verified] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Toyota Vitz 2016                                               │
│  📅 Posted: 2 hours ago                                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ "I need Toyota Vitz urgently in Nairobi.               │   │
│  │  Budget ready."                                        │   │
│  │                                                        │   │
│  │  AI Analysis: High urgency detected; Budget mentioned  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  📍 Nairobi              🌐 Telegram                           │
│  📅 2 hours ago          📢 Kenya Cars Marketplace             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  📞 0713241235                              [CALL]     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🔗 VIEW ORIGINAL POST (Telegram)                      │   │
│  │     Opens the real message on Telegram for verification│   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [  WHATSAPP  ]  [ COPY ]                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Card Sections

### 1. Temperature Header Bar (Full Width)
```
┌─────────────────────────────────────────┐
│ 🔥 HOT LEAD                    95/100 ✓│
└─────────────────────────────────────────┘
```
- **Color-coded bar**: Red (HOT), Amber (WARM), Blue (COLD), Gray (REJECT)
- **Emoji icon**: 🔥 ☀️ ❄️ ⚪
- **AI Score**: Shows 0-100 score
- **Verified badge**: If lead is verified

### 2. Product Title
```
Toyota Vitz 2016
📅 Posted: 2 hours ago
```
- Clear product name
- Freshness indicator

### 3. Intent Quote (Highlighted Box)
```
┌──────────────────────────────────┐
│ "I need Toyota Vitz urgently..." │
│                                  │
│ AI Analysis: High urgency...     │
└──────────────────────────────────┘
```
- Blue left border accent
- Original message text
- AI reasoning for the score

### 4. Trust Info Grid (2x2)
```
📍 Nairobi              🌐 Telegram
📅 2 hours ago          📢 Kenya Cars Marketplace
```
- Location
- Source platform
- Posted time
- Group/Channel name

### 5. Phone Number (PROMINENT)
```
┌─────────────────────────────────────────┐
│  📞 0713241235               [CALL]     │
└─────────────────────────────────────────┘
```
- Green background
- Large, bold font
- Call button
- Verified buyer phone only

### 6. View Original Post (CRITICAL)
```
┌─────────────────────────────────────────┐
│ 🔗 VIEW ORIGINAL POST (Telegram)        │
│ Opens the real message for verification │
└─────────────────────────────────────────┘
```
- Full-width blue button
- Platform name
- Trust message below

### 7. Action Buttons
```
[  WHATSAPP  ]  [ COPY ]
```
- WhatsApp one-tap
- Copy outreach message

## Data Requirements

### Required Fields
```json
{
  "text": "I need Toyota Vitz urgently in Nairobi. Budget ready.",
  "phone": "254713241235",
  "source": "Telegram",
  "url": "https://t.me/kenya_cars/83922",
  "timestamp": "2026-03-11T10:30:00",
  "ai_intent_score": 95,
  "ai_temperature": "HOT",
  "ai_score_reasoning": "High urgency detected; Budget mentioned",
  "title": "Toyota Vitz 2016",
  "location": "Nairobi",
  "channel_name": "Kenya Cars Marketplace",
  "is_verified": true,
  "whatsapp_url": "https://wa.me/254713241235?text=..."
}
```

## Features Implemented

✅ **AI Intent Scoring**
- Score: 0-100
- Temperature: HOT/WARM/COLD/REJECT
- Reasoning explanation

✅ **Phone Verification**
- Kenya format validation
- Display: 0713 241 235
- Verified buyer phones only

✅ **Freshness Filter**
- Shows posted time
- Fresh/Warm/Cold categorization

✅ **Trust Section**
- Location
- Source platform
- Group/Channel name
- Posted time

✅ **View Original Post**
- Prominent button
- Opens real source
- Verification message

✅ **One-Tap Actions**
- WhatsApp
- Call
- Copy outreach

## User Flow

1. **See Temperature** → Instantly know priority (HOT = act now)
2. **Read Quote** → Understand buyer's need
3. **Check Trust Info** → Verify source and location
4. **See Phone** → Contact buyer directly
5. **View Original** → Verify authenticity
6. **Take Action** → WhatsApp or Call

## Trust Indicators

| Element | Purpose |
|---------|---------|
| 🔥 Temperature | Priority level |
| ✓ Verified | Lead authenticity |
| 📍 Location | Geographic relevance |
| 🌐 Source | Platform origin |
| 📢 Group | Community context |
| 📅 Posted | Freshness |
| 🔗 View Post | Verification link |

## Example Cards

### HOT Lead (95/100)
```
🔥 HOT LEAD (95/100)
Toyota Vitz 2016
"I need Vitz urgently today!"
📍 Nairobi | 🌐 Telegram
📞 0713241235
[VIEW ORIGINAL POST]
```

### WARM Lead (65/100)
```
☀️ WARM LEAD (65/100)
Honda Fit 2018
"Looking for clean Fit"
📍 Mombasa | 🌐 Reddit
📞 0722555666
[VIEW ORIGINAL POST]
```

### COLD Lead (35/100)
```
❄️ COLD LEAD (35/100)
Any Car
"Thinking about buying"
📍 Kenya | 🌐 Forum
📞 0733777888
[VIEW ORIGINAL POST]
```

## Summary

The final lead card provides:
1. **Instant Priority** - Temperature badge
2. **Context** - Full quote + AI analysis
3. **Trust** - Source + verification link
4. **Action** - Phone + WhatsApp + View Post

Everything needed to verify and contact a lead in one view.
