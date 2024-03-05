// JavaScript code to handle chatbot functionality
document.addEventListener("DOMContentLoaded", function() {
    const chatbotButton = document.getElementById('chatbot-button');
    const chatbotContainer = document.getElementById('chatbot-container');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const clearButton = document.getElementById('clear-button');

    if (chatbotButton && chatbotContainer && chatMessages && userInput) {
        chatbotButton.addEventListener('click', () => {
            chatbotContainer.style.display = 'block';
        });

        // Function to handle sending message when Enter key is pressed
        userInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault(); // Prevent newline in textarea
                const message = userInput.value.trim();
                if (message !== '') {
                    addUserMessage(message);
                    userInput.value = '';
                }
            }
        });

        // Function to add user message to chat
        function addUserMessage(message) {
            const userDiv = document.createElement('div');
            userDiv.className = 'user-message';
            userDiv.textContent = message;
            chatMessages.appendChild(userDiv);
        }

        // Function to add bot message to chat
        function addBotMessage(message) {
            const botDiv = document.createElement('div');
            botDiv.className = 'bot-message';
            botDiv.textContent = message;
            chatMessages.appendChild(botDiv);
        }

        // Hide chatbox when clicking outside of it
        document.addEventListener('click', (event) => {
            if (!chatbotContainer.contains(event.target) && event.target !== chatbotButton) {
                chatbotContainer.style.display = 'none';
            }
        });

        // Clear text when clear button is clicked
        clearButton.addEventListener('click', function(event) {
            event.stopPropagation(); // Prevent the click event from propagating to the parent elements
            chatMessages.innerHTML = ''; // Clear chat messages
            clearButton.style.display = 'none'; // Hide the clear button
        });
    } else {
        console.error("One or more elements not found.");
    }
});
