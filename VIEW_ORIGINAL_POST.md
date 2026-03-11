# View Original Post - Critical Feature

## Overview

**This is a CRITICAL trust feature.** Every lead MUST have a "View Original Post" button that opens the real source message.

## Why This Matters

1. **Trust** - Users can verify the lead is real
2. **Transparency** - Shows exactly where the lead came from
3. **Context** - Users can see the full conversation/thread
4. **Verification** - Confirms the phone number is from that specific post

## Implementation

### UI Components Updated

1. **LeadCard.jsx** - Card view with prominent "View Original Post" button
2. **LeadDetail.jsx** - Detail modal with full-width source button

### Button Design

```jsx
// Full-width prominent button
<button className="w-full bg-gradient-to-r from-blue-600 to-blue-500 ...">
  <ExternalLink size={20} />
  View Original Post
  <span>(Telegram)</span>
</button>
<p className="text-center text-white/30 text-[10px] mt-2">
  Opens the real message on Telegram for verification
</p>
```

### Trust Section Layout

```
┌─────────────────────────────────────────┐
│ 📍 Kenya          🌐 Telegram           │
│ 🕒 3 hours ago    🔗 View Post          │
│ Channel: Kenya Car Buyers               │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  🔗 View Original Post (Telegram)       │
│     Opens the real message for          │
│     verification                        │
└─────────────────────────────────────────┘
```

## Backend Requirements

The lead object MUST include:
- `source_url` or `url` - Link to original post
- `source` or `source_platform` - Platform name (Telegram, Reddit, etc.)
- `group_name` / `channel_name` / `subreddit` - Group info (optional)

## Example Lead Data

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "text": "Looking for Toyota Vitz 2016",
  "phone": "0723898087",
  "source": "Telegram",
  "source_platform": "Telegram",
  "url": "https://t.me/kenya_cars/83922",
  "source_url": "https://t.me/kenya_cars/83922",
  "channel_name": "Kenya Car Buyers",
  "timestamp": "2026-03-08T10:33:00",
  "freshness": "fresh",
  "location": "Kenya"
}
```

## User Flow

1. User sees lead card with "View Original Post" button
2. User clicks button
3. New tab opens with the actual Telegram/Reddit/etc. post
4. User can verify:
   - The message exists
   - The phone number matches
   - It's actually a buyer post
   - The timestamp is correct

## Platforms Supported

- ✅ Telegram (t.me links)
- ✅ Reddit (reddit.com links)
- ✅ Facebook
- ✅ Twitter/X
- ✅ Forums
- ✅ Any web source with URL

## Trust Indicators Shown

1. **Source Icon** - Platform icon (Telegram, Reddit, etc.)
2. **Source Name** - Platform name clearly displayed
3. **Group/Channel** - Specific group/channel name
4. **Posted Time** - When the original post was made
5. **View Button** - Prominent button to open original

## Critical Checklist

- [x] Every lead card has "View Original Post" button
- [x] Button opens actual source URL in new tab
- [x] Source platform is clearly labeled
- [x] Group/channel info shown if available
- [x] Button is prominent and easy to find
- [x] Works on both card view and detail view

## Testing

```javascript
// Test View Original Post button
const lead = {
  source_url: "https://t.me/kenya_cars/83922",
  source: "Telegram",
  channel_name: "Kenya Car Buyers"
};

// Button should:
// 1. Display "View Original Post (Telegram)"
// 2. Open https://t.me/kenya_cars/83922 in new tab
// 3. Show "Channel: Kenya Car Buyers" above button
```

## Summary

**The "View Original Post" button is CRITICAL for trust.**

Without it, users cannot verify leads are real.
With it, users can instantly check the source and confirm authenticity.

✅ **Implemented in:**
- `LeadCard.jsx` - Card view
- `LeadDetail.jsx` - Detail modal

✅ **Shows:**
- Source platform
- Group/Channel name  
- Posted time
- Direct link to original post
