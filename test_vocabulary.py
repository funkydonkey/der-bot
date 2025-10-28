"""Test script for vocabulary service and agent."""
import asyncio
import sys

from config.logging_config import setup_logging
from database.database import init_database, async_session_maker
from services.vocabulary_service import VocabularyService
from agents.german_validator import german_validator

setup_logging()


async def test_vocabulary_flow():
    """Test the complete vocabulary management flow."""
    print("=" * 60)
    print("Testing Vocabulary Service and German Validator Agent")
    print("=" * 60)

    # Initialize database
    await init_database()

    async with async_session_maker() as session:
        vocab_service = VocabularyService(session)

        # Test 1: Create user
        print("\n1. Creating test user...")
        user = await vocab_service.get_or_create_user(
            telegram_id=999999,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        print(f"   ✓ User created: {user.telegram_id} ({user.username})")

        # Test 2: Add word without article
        print("\n2. Adding German word WITHOUT article...")
        word, validation = await vocab_service.add_word_with_validation(
            user=user,
            german_word="Hund",  # Without article
            translation="dog"
        )
        print(f"   Word: {word.full_german_word}")
        print(f"   Article: {word.article}")
        print(f"   Translation: {word.translation}")
        print(f"   Validation: {validation.is_correct}")
        print(f"   Feedback: {validation.feedback}")

        # Test 3: Add word WITH article
        print("\n3. Adding German word WITH article...")
        word2, validation2 = await vocab_service.add_word_with_validation(
            user=user,
            german_word="die Katze",  # With article
            translation="cat"
        )
        print(f"   Word: {word2.full_german_word}")
        print(f"   Article: {word2.article}")
        print(f"   Translation: {word2.translation}")
        print(f"   Validation: {validation2.is_correct}")
        print(f"   Feedback: {validation2.feedback}")

        # Test 4: Add word with wrong translation
        print("\n4. Adding word with WRONG translation...")
        word3, validation3 = await vocab_service.add_word_with_validation(
            user=user,
            german_word="Tisch",
            translation="fish"  # Wrong!
        )
        print(f"   Word: {word3.full_german_word}")
        print(f"   Translation provided: {word3.translation}")
        print(f"   Validation: {validation3.is_correct}")
        print(f"   Feedback: {validation3.feedback}")

        # Test 5: Get user words
        print("\n5. Retrieving all user words...")
        words = await vocab_service.get_user_words(user)
        print(f"   ✓ Found {len(words)} words:")
        for w in words:
            print(f"      - {w.full_german_word} = {w.translation}")

        # Test 6: Quiz flow
        print("\n6. Testing quiz flow...")
        quiz_word = await vocab_service.get_random_word_for_quiz(user)
        if quiz_word:
            print(f"   Quiz question: {quiz_word.full_german_word}")
            print(f"   Correct answer: {quiz_word.translation}")

            # Test correct answer
            print("\n   Testing CORRECT answer...")
            validation_correct = await vocab_service.validate_quiz_answer(
                quiz_word,
                quiz_word.translation
            )
            print(f"      Result: {validation_correct.is_correct}")
            print(f"      Feedback: {validation_correct.feedback}")

            # Test wrong answer
            print("\n   Testing WRONG answer...")
            validation_wrong = await vocab_service.validate_quiz_answer(
                quiz_word,
                "wrong answer"
            )
            print(f"      Result: {validation_wrong.is_correct}")
            print(f"      Feedback: {validation_wrong.feedback}")

        # Test 7: Word stats
        print("\n7. Checking word statistics...")
        count = await vocab_service.get_word_count(user)
        print(f"   ✓ Total words: {count}")

        for w in words:
            print(f"   - {w.full_german_word}")
            print(f"      Reviews: {w.total_reviews}")
            print(f"      Correct: {w.correct_count}")
            print(f"      Incorrect: {w.incorrect_count}")
            print(f"      Success rate: {w.success_rate:.0f}%")

    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(test_vocabulary_flow())
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
