# FAQ Bot - AI-Powered Chat Assistant

A modern FAQ bot built with Next.js and AWS Bedrock, featuring real-time streaming responses powered by Claude 4 Sonnet.

## Features

- 🤖 **AI-Powered Responses** - Uses AWS Bedrock with Claude 4 Sonnet for intelligent conversations
- 🔄 **Real-time Streaming** - Responses stream in real-time for better user experience
- 🎨 **Modern UI** - Clean, responsive interface with dark/light theme support
- 📱 **Mobile Friendly** - Optimized for both desktop and mobile devices
- 🔧 **Robust Error Handling** - Improved parsing and error recovery for streaming data

## Quick Start

1. **Install dependencies:**

   ```bash
   npm install
   ```

2. **Set up environment variables:**
   Create a `.env.local` file with your AWS credentials:

   ```env
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_REGION=ap-northeast-1
   ```

3. **Run the development server:**

   ```bash
   npm run dev
   ```

4. **Open your browser:**
   Visit [http://localhost:3000](http://localhost:3000) to start chatting with the AI assistant.

## Backend Integration

The frontend expects streaming responses in Server-Sent Events (SSE) format:

```
data: {"type": "content", "text": "Hello ", "timestamp": "2024-01-01T00:00:00.000Z"}

data: {"type": "done", "model": "Claude", "timestamp": "2024-01-01T00:00:00.000Z"}
```

For plain JSON streaming, the frontend now supports both formats automatically.

## Recent Improvements

- ✅ Enhanced streaming data parsing with better error handling
- ✅ Support for both SSE and plain JSON streaming formats
- ✅ Improved error logging for debugging streaming issues
- ✅ Graceful handling of malformed or incomplete data chunks

## Tech Stack

- **Frontend:** Next.js 14, React, TypeScript, Tailwind CSS
- **Backend:** AWS Bedrock, Claude 4 Sonnet
- **UI Components:** Radix UI, Lucide Icons
- **Streaming:** Server-Sent Events (SSE) / JSON streaming

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## License

MIT License - feel free to use this project for your own FAQ bot implementations.
