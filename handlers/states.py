"""FSM states for bot conversations."""
from aiogram.fsm.state import State, StatesGroup


class AddWordStates(StatesGroup):
    """States for adding a new word."""
    waiting_for_german = State()


class QuizStates(StatesGroup):
    """States for quiz mode."""
    waiting_for_answer = State()