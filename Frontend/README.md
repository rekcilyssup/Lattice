<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/45ae0bdf-180c-4f7f-a756-f5b5e7e6ee0f

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Set frontend env in `.env.local`:
   - `NEXT_PUBLIC_API_BASE_URL=http://localhost:8080/api/v1`
   - Optional: `GEMINI_API_KEY` (if you still use direct Gemini features)
3. Run the app:
   `npm run dev`
