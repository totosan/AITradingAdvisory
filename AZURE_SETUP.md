# Azure OpenAI Setup Instructions

## Step 1: Get Your Azure OpenAI Credentials

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your **Azure OpenAI** resource
3. Go to **Keys and Endpoint** section
4. Copy the following:
   - **KEY 1** or **KEY 2** (either works)
   - **Endpoint** (looks like: `https://your-resource-name.openai.azure.com/`)
   - **Deployment name** (e.g., `gpt-4o`, `gpt-4`, `gpt-35-turbo`)

## Step 2: Update Your .env File

Open `.env` file and update these values:

```bash
# Set provider to azure
LLM_PROVIDER=azure

# Paste your credentials here
AZURE_OPENAI_API_KEY=your-actual-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

## Step 3: Rebuild and Run

```bash
# Rebuild the Docker container
docker-compose down
docker-compose build
docker-compose up -d

# Run the application
make run
```

## Recommended Models

- **gpt-4o** - Best for complex analysis with function calling (recommended)
- **gpt-4** - Very capable, slightly slower
- **gpt-35-turbo** - Fast and cost-effective

## Troubleshooting

### Error: "Azure OpenAI credentials not found"
- Make sure you've set `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` in `.env`
- Check for typos in the variable names

### Error: "Deployment not found"
- Verify your deployment name in Azure Portal matches `AZURE_OPENAI_DEPLOYMENT`
- Common names: `gpt-4o`, `gpt-4`, `gpt-35-turbo`, `gpt-4-turbo`

### Error: "Invalid API version"
- Try `2024-02-15-preview` or `2023-12-01-preview`
- Check supported versions in Azure Portal

## Benefits of Azure OpenAI

✅ **Excellent function calling** - Tools work reliably  
✅ **Better reasoning** - More accurate analysis  
✅ **Faster responses** - Lower latency than local models  
✅ **Enterprise security** - Data stays in your Azure tenant  
✅ **No local GPU required** - Runs entirely in the cloud
