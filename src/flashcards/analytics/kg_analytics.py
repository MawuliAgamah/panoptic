"""Knowledge Graph performance analytics for flashcards"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import statistics
from ..models.flashcard import Flashcard
from ..models.knowledge_graph import KGMapping, KGEntity, KGTopic


@dataclass
class EntityPerformance:
    """Performance metrics for a specific entity"""
    entity_id: str
    entity_name: str
    entity_type: str

    # Card counts
    total_cards: int = 0
    cards_mastered: int = 0  # High ease factor or low difficulty
    cards_struggling: int = 0  # Low ease factor or high difficulty

    # Performance metrics
    avg_ease_factor: float = 0.0
    avg_difficulty: float = 0.0
    avg_correct_streak: float = 0.0
    avg_total_reviews: float = 0.0

    # Learning efficiency
    mastery_rate: float = 0.0  # cards_mastered / total_cards
    struggle_rate: float = 0.0  # cards_struggling / total_cards

    def calculate_strength_score(self) -> float:
        """Calculate overall strength score for this entity (0-10)"""
        if self.total_cards == 0:
            return 0.0

        # Weighted score based on multiple factors
        mastery_weight = self.mastery_rate * 4.0
        ease_weight = min(self.avg_ease_factor / 3.0, 2.0)  # Cap at 2.0
        streak_weight = min(self.avg_correct_streak / 5.0, 2.0)  # Cap at 2.0
        struggle_penalty = self.struggle_rate * 2.0

        score = mastery_weight + ease_weight + streak_weight - struggle_penalty
        return max(0.0, min(score, 10.0))


@dataclass
class TopicPerformance:
    """Performance metrics for a specific topic/domain"""
    topic_id: str
    topic_name: str
    category: str

    # Card and entity counts
    total_cards: int = 0
    unique_entities: int = 0

    # Performance aggregates
    avg_entity_strength: float = 0.0
    topic_complexity: float = 0.0  # Based on interconnections

    # Learning patterns
    cards_per_entity: float = 0.0
    mastery_distribution: Dict[str, int] = None  # "easy", "medium", "hard"

    def __post_init__(self):
        if self.mastery_distribution is None:
            self.mastery_distribution = {"easy": 0, "medium": 0, "hard": 0}

    def calculate_topic_score(self) -> float:
        """Calculate overall topic mastery score (0-10)"""
        if self.total_cards == 0:
            return 0.0

        # Weight based on entity strength and distribution
        strength_component = self.avg_entity_strength

        # Bonus for well-distributed learning (not just memorizing isolated facts)
        if self.unique_entities > 0:
            coverage_bonus = min(self.cards_per_entity, 2.0)  # Cap at 2.0
        else:
            coverage_bonus = 0.0

        # Complexity adjustment (higher complexity topics get slight bonus for same performance)
        complexity_bonus = min(self.topic_complexity * 0.1, 0.5)

        score = strength_component + coverage_bonus + complexity_bonus
        return max(0.0, min(score, 10.0))


@dataclass
class LearningInsight:
    """Individual insight about learning patterns"""
    insight_type: str  # "strength", "weakness", "opportunity", "pattern"
    title: str
    description: str
    confidence: float  # 0.0-1.0
    actionable_suggestion: str
    related_entities: List[str] = None
    related_topics: List[str] = None

    def __post_init__(self):
        if self.related_entities is None:
            self.related_entities = []
        if self.related_topics is None:
            self.related_topics = []


class KGPerformanceAnalytics:
    """Knowledge Graph performance analytics engine"""

    def __init__(self):
        self.min_cards_for_insight = 3  # Minimum cards needed to generate insights
        self.mastery_ease_threshold = 2.8  # Ease factor threshold for "mastered"
        self.struggle_ease_threshold = 2.2  # Ease factor threshold for "struggling"
        self.mastery_difficulty_threshold = 0.3  # Difficulty threshold for "mastered"
        self.struggle_difficulty_threshold = 0.7  # Difficulty threshold for "struggling"

    def analyze_entity_performance(self, cards: List[Flashcard]) -> Dict[str, EntityPerformance]:
        """Analyze performance for all entities across given flashcards"""
        entity_cards = defaultdict(list)

        # Group cards by entity
        for card in cards:
            if card.kg_mapping:
                for entity in card.kg_mapping.get_all_entities():
                    entity_cards[entity.entity_id].append(card)

        entity_performances = {}

        for entity_id, entity_cards_list in entity_cards.items():
            if not entity_cards_list:
                continue

            # Get entity info from first card
            sample_entity = None
            for card in entity_cards_list:
                for entity in card.kg_mapping.get_all_entities():
                    if entity.entity_id == entity_id:
                        sample_entity = entity
                        break
                if sample_entity:
                    break

            if not sample_entity:
                continue

            performance = EntityPerformance(
                entity_id=entity_id,
                entity_name=sample_entity.name,
                entity_type=sample_entity.entity_type,
                total_cards=len(entity_cards_list)
            )

            # Calculate metrics
            ease_factors = []
            difficulties = []
            correct_streaks = []
            total_reviews = []

            for card in entity_cards_list:
                scheduling = card.scheduling
                ease_factors.append(scheduling.ease_factor)
                difficulties.append(scheduling.difficulty)
                correct_streaks.append(scheduling.correct_streak)
                total_reviews.append(scheduling.total_reviews)

                # Classify card difficulty
                if (scheduling.ease_factor >= self.mastery_ease_threshold or
                    scheduling.difficulty <= self.mastery_difficulty_threshold):
                    performance.cards_mastered += 1
                elif (scheduling.ease_factor <= self.struggle_ease_threshold or
                      scheduling.difficulty >= self.struggle_difficulty_threshold):
                    performance.cards_struggling += 1

            # Calculate averages
            performance.avg_ease_factor = statistics.mean(ease_factors) if ease_factors else 0.0
            performance.avg_difficulty = statistics.mean(difficulties) if difficulties else 0.0
            performance.avg_correct_streak = statistics.mean(correct_streaks) if correct_streaks else 0.0
            performance.avg_total_reviews = statistics.mean(total_reviews) if total_reviews else 0.0

            # Calculate rates
            if performance.total_cards > 0:
                performance.mastery_rate = performance.cards_mastered / performance.total_cards
                performance.struggle_rate = performance.cards_struggling / performance.total_cards

            entity_performances[entity_id] = performance

        return entity_performances

    def analyze_topic_performance(self, cards: List[Flashcard],
                                entity_performances: Dict[str, EntityPerformance]) -> Dict[str, TopicPerformance]:
        """Analyze performance for all topics across given flashcards"""
        topic_cards = defaultdict(list)
        topic_entities = defaultdict(set)

        # Group cards by topic and track entities per topic
        for card in cards:
            if card.kg_mapping:
                card_entities = set()
                for entity in card.kg_mapping.get_all_entities():
                    card_entities.add(entity.entity_id)

                for topic in card.kg_mapping.get_all_topics():
                    topic_cards[topic.topic_id].append(card)
                    topic_entities[topic.topic_id].update(card_entities)

        topic_performances = {}

        for topic_id, topic_cards_list in topic_cards.items():
            if not topic_cards_list:
                continue

            # Get topic info from first card
            sample_topic = None
            for card in topic_cards_list:
                for topic in card.kg_mapping.get_all_topics():
                    if topic.topic_id == topic_id:
                        sample_topic = topic
                        break
                if sample_topic:
                    break

            if not sample_topic:
                continue

            performance = TopicPerformance(
                topic_id=topic_id,
                topic_name=sample_topic.name,
                category=sample_topic.category,
                total_cards=len(topic_cards_list),
                unique_entities=len(topic_entities[topic_id])
            )

            # Calculate entity strength average for this topic
            topic_entity_performances = []
            for entity_id in topic_entities[topic_id]:
                if entity_id in entity_performances:
                    topic_entity_performances.append(entity_performances[entity_id].calculate_strength_score())

            if topic_entity_performances:
                performance.avg_entity_strength = statistics.mean(topic_entity_performances)

            # Calculate complexity based on relationships and entity diversity
            if performance.unique_entities > 0:
                performance.cards_per_entity = performance.total_cards / performance.unique_entities

                # Complexity increases with more entities and relationships
                relationship_count = sum(
                    len(card.kg_mapping.tested_relationships)
                    for card in topic_cards_list
                    if card.kg_mapping
                )
                performance.topic_complexity = (
                    (performance.unique_entities * 0.3) +
                    (relationship_count * 0.5) +
                    (performance.cards_per_entity * 0.2)
                ) / performance.total_cards

            # Analyze mastery distribution
            mastery_counts = {"easy": 0, "medium": 0, "hard": 0}
            for card in topic_cards_list:
                difficulty_level = card.get_difficulty_level().lower()
                if difficulty_level in mastery_counts:
                    mastery_counts[difficulty_level] += 1

            performance.mastery_distribution = mastery_counts
            topic_performances[topic_id] = performance

        return topic_performances

    def generate_learning_insights(self, cards: List[Flashcard],
                                 entity_performances: Dict[str, EntityPerformance],
                                 topic_performances: Dict[str, TopicPerformance]) -> List[LearningInsight]:
        """Generate actionable learning insights based on performance data"""
        insights = []

        if len(cards) < self.min_cards_for_insight:
            return insights

        # Entity-based insights
        insights.extend(self._generate_entity_insights(entity_performances))

        # Topic-based insights
        insights.extend(self._generate_topic_insights(topic_performances))

        # Cross-cutting insights
        insights.extend(self._generate_pattern_insights(cards, entity_performances, topic_performances))

        # Sort by confidence and importance
        insights.sort(key=lambda x: (x.confidence, len(x.related_entities) + len(x.related_topics)), reverse=True)

        return insights[:10]  # Return top 10 insights

    def _generate_entity_insights(self, entity_performances: Dict[str, EntityPerformance]) -> List[LearningInsight]:
        """Generate insights about specific entities"""
        insights = []

        # Find strongest and weakest entities
        performances = list(entity_performances.values())
        if len(performances) < 2:
            return insights

        performances_with_sufficient_cards = [p for p in performances if p.total_cards >= self.min_cards_for_insight]

        if not performances_with_sufficient_cards:
            return insights

        # Strongest entity
        strongest = max(performances_with_sufficient_cards, key=lambda x: x.calculate_strength_score())
        if strongest.calculate_strength_score() > 7.0:
            insights.append(LearningInsight(
                insight_type="strength",
                title=f"Strong mastery of {strongest.entity_name}",
                description=f"You've mastered {strongest.entity_name} with {strongest.mastery_rate:.1%} of cards at mastery level and an average streak of {strongest.avg_correct_streak:.1f}.",
                confidence=min(0.9, strongest.total_cards / 10),
                actionable_suggestion=f"Consider reviewing related concepts or teaching {strongest.entity_name} to reinforce your understanding.",
                related_entities=[strongest.entity_name]
            ))

        # Weakest entity
        weakest = min(performances_with_sufficient_cards, key=lambda x: x.calculate_strength_score())
        if weakest.calculate_strength_score() < 4.0:
            insights.append(LearningInsight(
                insight_type="weakness",
                title=f"Opportunity to improve {weakest.entity_name}",
                description=f"{weakest.entity_name} shows lower performance with {weakest.struggle_rate:.1%} of cards in struggle range and average ease factor of {weakest.avg_ease_factor:.2f}.",
                confidence=min(0.9, weakest.total_cards / 10),
                actionable_suggestion=f"Focus extra review time on {weakest.entity_name}. Break it down into smaller concepts or find additional learning resources.",
                related_entities=[weakest.entity_name]
            ))

        return insights

    def _generate_topic_insights(self, topic_performances: Dict[str, TopicPerformance]) -> List[LearningInsight]:
        """Generate insights about topic domains"""
        insights = []

        performances = list(topic_performances.values())
        if len(performances) < 2:
            return insights

        performances_with_sufficient_cards = [p for p in performances if p.total_cards >= self.min_cards_for_insight]

        if not performances_with_sufficient_cards:
            return insights

        # Best performing topic
        best_topic = max(performances_with_sufficient_cards, key=lambda x: x.calculate_topic_score())
        if best_topic.calculate_topic_score() > 6.0:
            insights.append(LearningInsight(
                insight_type="strength",
                title=f"Strong foundation in {best_topic.topic_name}",
                description=f"Your {best_topic.topic_name} knowledge is well-developed with {best_topic.unique_entities} entities covered and strong performance across the domain.",
                confidence=min(0.8, best_topic.total_cards / 15),
                actionable_suggestion=f"Consider exploring advanced topics within {best_topic.topic_name} or connecting it to other domains.",
                related_topics=[best_topic.topic_name]
            ))

        # Topic needing attention
        weak_topic = min(performances_with_sufficient_cards, key=lambda x: x.calculate_topic_score())
        if weak_topic.calculate_topic_score() < 4.0:
            insights.append(LearningInsight(
                insight_type="opportunity",
                title=f"Strengthen {weak_topic.topic_name} foundation",
                description=f"{weak_topic.topic_name} could benefit from more focused study with current performance indicating gaps in understanding.",
                confidence=min(0.8, weak_topic.total_cards / 15),
                actionable_suggestion=f"Dedicate extra study sessions to {weak_topic.topic_name}. Create more flashcards covering fundamental concepts.",
                related_topics=[weak_topic.topic_name]
            ))

        return insights

    def _generate_pattern_insights(self, cards: List[Flashcard],
                                 entity_performances: Dict[str, EntityPerformance],
                                 topic_performances: Dict[str, TopicPerformance]) -> List[LearningInsight]:
        """Generate insights about learning patterns across entities and topics"""
        insights = []

        if len(cards) < 5:
            return insights

        # Analyze review frequency patterns
        total_reviews = [card.scheduling.total_reviews for card in cards]
        avg_reviews = statistics.mean(total_reviews) if total_reviews else 0

        under_reviewed_cards = [card for card in cards if card.scheduling.total_reviews < avg_reviews * 0.5]

        if len(under_reviewed_cards) > len(cards) * 0.3:  # More than 30% under-reviewed
            insights.append(LearningInsight(
                insight_type="pattern",
                title="Some cards need more review cycles",
                description=f"{len(under_reviewed_cards)} cards have significantly fewer reviews than average, which may indicate inconsistent study habits.",
                confidence=0.7,
                actionable_suggestion="Consider setting up a regular review schedule to ensure all cards get adequate practice."
            ))

        # Analyze difficulty distribution
        difficulty_levels = [card.get_difficulty_level() for card in cards]
        difficulty_counts = Counter(difficulty_levels)

        if difficulty_counts.get("Hard", 0) > len(cards) * 0.5:
            insights.append(LearningInsight(
                insight_type="pattern",
                title="High proportion of difficult cards",
                description=f"Over half of your cards are in the 'Hard' difficulty range, suggesting the material may be challenging or needs different learning strategies.",
                confidence=0.8,
                actionable_suggestion="Consider breaking difficult cards into smaller, more specific questions or using different memory techniques."
            ))

        return insights

    def get_learning_dashboard_data(self, cards: List[Flashcard]) -> Dict[str, Any]:
        """Get comprehensive dashboard data for learning analytics"""
        entity_performances = self.analyze_entity_performance(cards)
        topic_performances = self.analyze_topic_performance(cards, entity_performances)
        insights = self.generate_learning_insights(cards, entity_performances, topic_performances)

        # Calculate overall metrics
        total_entities = len(entity_performances)
        total_topics = len(topic_performances)

        if entity_performances:
            avg_entity_strength = statistics.mean(
                perf.calculate_strength_score() for perf in entity_performances.values()
            )
        else:
            avg_entity_strength = 0.0

        if topic_performances:
            avg_topic_score = statistics.mean(
                perf.calculate_topic_score() for perf in topic_performances.values()
            )
        else:
            avg_topic_score = 0.0

        # Strength/weakness summaries
        top_entities = sorted(
            entity_performances.values(),
            key=lambda x: x.calculate_strength_score(),
            reverse=True
        )[:5]

        weak_entities = sorted(
            [p for p in entity_performances.values() if p.total_cards >= self.min_cards_for_insight],
            key=lambda x: x.calculate_strength_score()
        )[:5]

        return {
            "overview": {
                "total_cards": len(cards),
                "total_entities": total_entities,
                "total_topics": total_topics,
                "avg_entity_strength": avg_entity_strength,
                "avg_topic_score": avg_topic_score
            },
            "entities": {
                "performances": {eid: perf for eid, perf in entity_performances.items()},
                "top_performers": top_entities,
                "need_attention": weak_entities
            },
            "topics": {
                "performances": {tid: perf for tid, perf in topic_performances.items()},
                "strongest": max(topic_performances.values(), key=lambda x: x.calculate_topic_score()) if topic_performances else None,
                "weakest": min(topic_performances.values(), key=lambda x: x.calculate_topic_score()) if topic_performances else None
            },
            "insights": insights,
            "generated_at": datetime.now().isoformat()
        }