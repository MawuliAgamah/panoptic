"""Example: How to use improved flashcard service in web API"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from typing import List, Optional
import tempfile
import os

from flashcards.services.improved_flashcard_service import create_flashcard_orchestrator


app = FastAPI(title="AI Module Flashcard API")

# Global service instance
flashcard_orchestrator = create_flashcard_orchestrator()


# Pydantic models for API
class CreateCardRequest(BaseModel):
    front: str
    back: str
    domains: Optional[List[str]] = []
    algorithm: str = "sm2"

class ReviewCardRequest(BaseModel):
    quality: int  # 1-5 scale
    response_time_seconds: Optional[float] = None

class CreateDeckRequest(BaseModel):
    name: str
    description: str = ""
    algorithm: str = "sm2"

class StudySessionResponse(BaseModel):
    success: bool
    cards: List[dict]
    session_info: dict
    error: Optional[str] = None


# API Endpoints

@app.post("/api/users/{user_id}/cards")
async def create_card(user_id: str, card_data: CreateCardRequest):
    """Create a new flashcard"""
    
    result = flashcard_orchestrator.create_card(
        user_id=user_id,
        front=card_data.front,
        back=card_data.back,
        domains=card_data.domains,
        algorithm=card_data.algorithm
    )
    
    if result.success:
        card = result.data
        return {
            "success": True,
            "card": {
                "id": card.id,
                "front": card.front,
                "back": card.back,
                "domains": card.Domains,
                "created_at": card.created_at.isoformat(),
                "next_review": card.scheduling.next_review_date.isoformat()
            }
        }
    else:
        raise HTTPException(status_code=400, detail=result.error)


@app.get("/api/users/{user_id}/study-session")
async def get_study_session(user_id: str, limit: int = 5):
    """Get cards for study session"""
    
    # Get due cards
    due_result = flashcard_orchestrator.get_due_cards(user_id, limit=limit)
    
    if not due_result.success:
        raise HTTPException(status_code=400, detail=due_result.error)
    
    # Get user stats
    stats_result = flashcard_orchestrator.get_user_stats(user_id)
    stats = stats_result.data if stats_result.success else {}
    
    # Convert cards to dict format
    cards_data = []
    for card in due_result.data:
        cards_data.append({
            "id": card.id,
            "front": card.front,
            "back": card.back,
            "domains": card.Domains,
            "ease_factor": card.scheduling.ease_factor,
            "interval_days": card.scheduling.interval_days
        })
    
    return {
        "success": True,
        "cards": cards_data,
        "session_info": {
            "cards_in_session": len(cards_data),
            "total_cards": stats.get("total_cards", 0),
            "cards_due": stats.get("cards_due", 0),
            "average_ease_factor": stats.get("average_ease_factor", 0)
        }
    }


@app.post("/api/cards/{card_id}/review")
async def review_card(card_id: str, review_data: ReviewCardRequest):
    """Process a card review"""
    
    result = flashcard_orchestrator.review_card(
        card_id=card_id,
        quality=review_data.quality,
        response_time=review_data.response_time_seconds
    )
    
    if result.success:
        review = result.data
        return {
            "success": True,
            "review": {
                "id": review.review_id,
                "quality": review.quality,
                "response_time": review.response_time_seconds,
                "reviewed_at": review.reviewed_at.isoformat()
            },
            "next_review_date": review.reviewed_at.isoformat()  # Updated card schedule
        }
    else:
        raise HTTPException(status_code=400, detail=result.error)


@app.post("/api/users/{user_id}/decks")
async def create_deck(user_id: str, deck_data: CreateDeckRequest):
    """Create a new deck"""
    
    result = flashcard_orchestrator.create_deck(
        user_id=user_id,
        name=deck_data.name,
        description=deck_data.description,
        algorithm=deck_data.algorithm
    )
    
    if result.success:
        deck = result.data
        return {
            "success": True,
            "deck": {
                "id": deck.deck_id,
                "name": deck.name,
                "description": deck.description,
                "algorithm": deck.default_algorithm,
                "created_at": deck.created_at.isoformat()
            }
        }
    else:
        raise HTTPException(status_code=400, detail=result.error)


@app.get("/api/users/{user_id}/decks")
async def get_user_decks(user_id: str):
    """Get all decks for user"""
    
    result = flashcard_orchestrator.get_user_decks(user_id)
    
    if result.success:
        decks_data = []
        for deck in result.data:
            decks_data.append({
                "id": deck.deck_id,
                "name": deck.name,
                "description": deck.description,
                "algorithm": deck.default_algorithm,
                "created_at": deck.created_at.isoformat()
            })
        
        return {"success": True, "decks": decks_data}
    else:
        raise HTTPException(status_code=400, detail=result.error)


@app.post("/api/users/{user_id}/documents/upload")
async def upload_document_for_flashcards(
    user_id: str, 
    file: UploadFile = File(...),
    generate_flashcards: bool = True
):
    """Upload document and optionally generate flashcards"""
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name
    
    try:
        # Use your main app logic
        from examples.main_app_usage import AIModuleApp
        app_instance = AIModuleApp()
        
        result = await app_instance.process_document_with_flashcards(
            document_path=tmp_file_path,
            user_id=user_id,
            generate_flashcards=generate_flashcards
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Document processed successfully",
                "flashcards_created": result["flashcards_created"],
                "document_id": result["document_processed"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    
    finally:
        # Clean up temp file
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)


@app.get("/api/users/{user_id}/stats")
async def get_user_stats(user_id: str):
    """Get comprehensive user statistics"""
    
    result = flashcard_orchestrator.get_user_stats(user_id)
    
    if result.success:
        return {"success": True, "stats": result.data}
    else:
        raise HTTPException(status_code=400, detail=result.error)


@app.post("/api/users/{user_id}/sync/anki")
async def sync_with_anki(user_id: str):
    """Sync user's flashcards with Anki"""
    
    result = flashcard_orchestrator.sync_with_anki(user_id)
    
    if result.success:
        return {
            "success": True,
            "message": "Sync completed",
            "sync_results": result.data
        }
    else:
        raise HTTPException(status_code=400, detail=result.error)


# Frontend HTML (simple example)
@app.get("/flashcards")
async def flashcards_ui():
    """Simple flashcard interface"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Module Flashcards</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .card { border: 1px solid #ddd; padding: 20px; margin: 10px; border-radius: 8px; }
            .button { padding: 10px 20px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; }
            .primary { background-color: #007bff; color: white; }
            .success { background-color: #28a745; color: white; }
            .warning { background-color: #ffc107; color: black; }
        </style>
    </head>
    <body>
        <h1>🧠 AI Module Flashcards</h1>
        
        <div id="study-session" style="display: none;">
            <div class="card">
                <h3>Study Session</h3>
                <div id="card-content"></div>
                <div id="answer-content" style="display: none;"></div>
                <div id="card-buttons"></div>
            </div>
        </div>
        
        <div id="controls">
            <button class="button primary" onclick="startStudySession()">Start Study Session</button>
            <button class="button primary" onclick="showCreateCard()">Create Flashcard</button>
            <button class="button primary" onclick="uploadDocument()">Upload Document</button>
            <button class="button primary" onclick="syncAnki()">Sync with Anki</button>
        </div>
        
        <div id="create-card" style="display: none;">
            <div class="card">
                <h3>Create New Flashcard</h3>
                <input type="text" id="front-text" placeholder="Front (Question)" style="width: 100%; margin: 5px 0;">
                <textarea id="back-text" placeholder="Back (Answer)" style="width: 100%; margin: 5px 0; height: 100px;"></textarea>
                <button class="button success" onclick="createCard()">Create Card</button>
                <button class="button" onclick="hideCreateCard()">Cancel</button>
            </div>
        </div>
        
        <div id="stats" class="card">
            <h3>📊 Your Stats</h3>
            <div id="stats-content">Loading...</div>
        </div>

        <script>
            const USER_ID = 'demo_user';  // In real app, get from authentication
            let currentSession = null;
            let currentCardIndex = 0;

            async function startStudySession() {
                const response = await fetch(`/api/users/${USER_ID}/study-session`);
                const data = await response.json();
                
                if (data.success && data.cards.length > 0) {
                    currentSession = data;
                    currentCardIndex = 0;
                    document.getElementById('study-session').style.display = 'block';
                    showCurrentCard();
                } else {
                    alert('No cards due for review!');
                }
            }

            function showCurrentCard() {
                const card = currentSession.cards[currentCardIndex];
                document.getElementById('card-content').innerHTML = `
                    <h4>Card ${currentCardIndex + 1}/${currentSession.cards.length}</h4>
                    <p><strong>Question:</strong> ${card.front}</p>
                `;
                document.getElementById('answer-content').style.display = 'none';
                document.getElementById('card-buttons').innerHTML = `
                    <button class="button primary" onclick="showAnswer()">Show Answer</button>
                    <button class="button" onclick="skipCard()">Skip</button>
                `;
            }

            function showAnswer() {
                const card = currentSession.cards[currentCardIndex];
                document.getElementById('answer-content').innerHTML = `
                    <p><strong>Answer:</strong> ${card.back}</p>
                `;
                document.getElementById('answer-content').style.display = 'block';
                document.getElementById('card-buttons').innerHTML = `
                    <p>How well did you know this?</p>
                    <button class="button warning" onclick="reviewCard(1)">😰 Hard</button>
                    <button class="button primary" onclick="reviewCard(3)">😐 OK</button>
                    <button class="button success" onclick="reviewCard(5)">😊 Easy</button>
                `;
            }

            async function reviewCard(quality) {
                const card = currentSession.cards[currentCardIndex];
                const response = await fetch(`/api/cards/${card.id}/review`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({quality: quality})
                });
                
                const result = await response.json();
                if (result.success) {
                    currentCardIndex++;
                    if (currentCardIndex < currentSession.cards.length) {
                        showCurrentCard();
                    } else {
                        endSession();
                    }
                }
            }

            function endSession() {
                document.getElementById('study-session').style.display = 'none';
                alert('🎉 Study session complete!');
                loadStats();
            }

            function showCreateCard() {
                document.getElementById('create-card').style.display = 'block';
            }

            function hideCreateCard() {
                document.getElementById('create-card').style.display = 'none';
            }

            async function createCard() {
                const front = document.getElementById('front-text').value;
                const back = document.getElementById('back-text').value;
                
                if (!front || !back) {
                    alert('Please fill in both front and back');
                    return;
                }

                const response = await fetch(`/api/users/${USER_ID}/cards`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        front: front,
                        back: back,
                        domains: ['web_interface']
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('✅ Flashcard created!');
                    hideCreateCard();
                    document.getElementById('front-text').value = '';
                    document.getElementById('back-text').value = '';
                    loadStats();
                }
            }

            async function loadStats() {
                const response = await fetch(`/api/users/${USER_ID}/stats`);
                const data = await response.json();
                
                if (data.success) {
                    const stats = data.stats;
                    document.getElementById('stats-content').innerHTML = `
                        <p>📚 Total Cards: ${stats.total_cards}</p>
                        <p>⏰ Cards Due: ${stats.cards_due}</p>
                        <p>📈 Average Ease: ${stats.average_ease_factor.toFixed(2)}</p>
                        <p>✅ Reviewed Today: ${stats.cards_reviewed_today}</p>
                    `;
                }
            }

            // Load stats on page load
            loadStats();
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
