const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

// Send Message
export const sendMessage = async (message: string) => {
  try {
    const response = await fetch(`${API_BASE_URL}/send_message/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message }),
    });

    return await response.json();
  } catch (error) {
    console.error("API Error:", error);
    return {
      response: "# Error\nThe agent is overworked and is taking a break. 😓",
    };
  }
};

// Upload Training Image
export const uploadTrainingImage = async (
  characterName: string,
  imageFile: File
) => {
  try {
    const formData = new FormData();
    formData.append("character_name", characterName);
    formData.append("character_image", imageFile);
    const response = await fetch(`${API_BASE_URL}/upload_training_image/`, {
      method: "POST",
      body: formData,
    });
    return await response.json();
  } catch (error) {
    console.error("upload training image Error:", error);
    return {
      status: "error",
      message: "Failed to upload training image. Please try again later.",
    };
  }
};

// Check Status
export async function checkStatus(taskId: string) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/check_training_status/?task_id=${taskId}`
    );
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error check status", error);
  }
}

// Fetch nfts
export async function fetchNFTs(address: string) {
  try {
    const response = await fetch(`${API_BASE_URL}/fetch_nfts/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address }),
    });
    return response.json();
  } catch (error) {
    console.error("Error fetch NFTs", error);
  }
}

// generateWithIpa
export async function generateWithIpa(message: string, externalUrl: string) {
  try {
    message = message.replace('Please Generate image with IPA ', '');
    const response = await fetch(`${externalUrl}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({prompt: message, aspect_ratio: "square", seed: 42}),
    });

    return await response.json();
  } catch (error) {
    console.error("API Error:", error);
    return {
      response: "# Error\nThe agent is overworked and is taking a break. 😓",
    };
  }
}

// twit to takoyan ai
export async function twitToTakoyanAi(agentKey:string, characterName:string, targetMessage:string, handle:string){
  try {
    const response = await fetch(`https://api-ai-agent.playarts.ai/twit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({agentKey, characterName, targetMessage, handle}),
    });

    return await response.json();
  } catch (error) {
    console.error("API Error:", error);
    return {
      response: "# Error\nThe agent is overworked and is taking a break. 😓",
    };
  }
}