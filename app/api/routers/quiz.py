from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_role
from app.db.session import get_db
from app.models import Course, Lesson, Module, QuizOption, QuizQuestion, User
from app.schemas.quiz import (
    QuizOptionCreate,
    QuizOptionOut,
    QuizOptionPublicOut,
    QuizOptionUpdate,
    QuizQuestionCreate,
    QuizQuestionOut,
    QuizQuestionPublicOut,
    QuizQuestionUpdate,
    QuizSubmitIn,
    QuizSubmitOut,
)

router = APIRouter()


async def _get_lesson_or_404(db: AsyncSession, lesson_id: int) -> Lesson:
    res = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = res.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


async def _get_question_or_404(db: AsyncSession, question_id: int) -> QuizQuestion:
    res = await db.execute(
        select(QuizQuestion)
        .options(selectinload(QuizQuestion.options))
        .where(QuizQuestion.id == question_id)
    )
    question = res.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Quiz question not found")
    return question


async def _get_option_or_404(db: AsyncSession, option_id: int) -> QuizOption:
    res = await db.execute(select(QuizOption).where(QuizOption.id == option_id))
    option = res.scalar_one_or_none()
    if not option:
        raise HTTPException(status_code=404, detail="Quiz option not found")
    return option


async def _require_quiz_editor(
    db: AsyncSession,
    lesson_id: int,
    user: User,
) -> Lesson:
    lesson = await _get_lesson_or_404(db, lesson_id)

    res = await db.execute(select(Module).where(Module.id == lesson.module_id))
    module = res.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    res = await db.execute(select(Course).where(Course.id == module.course_id))
    course = res.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if user.role != "admin" and course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="Not your course")

    return lesson


async def _ensure_single_correct_option(db: AsyncSession, question_id: int) -> None:
    res = await db.execute(
        select(QuizOption).where(
            QuizOption.question_id == question_id,
            QuizOption.is_correct.is_(True),
        )
    )
    correct_options = list(res.scalars().all())
    if len(correct_options) == 0:
        raise HTTPException(
            status_code=400,
            detail="Each question must have exactly one correct option",
        )
    if len(correct_options) > 1:
        raise HTTPException(
            status_code=400,
            detail="A question cannot have more than one correct option",
        )


# ----------------------------
# STUDENT / PUBLIC QUIZ ROUTES
# ----------------------------


@router.get(
    "/lessons/{lesson_id}/quiz",
    response_model=list[QuizQuestionPublicOut],
)
async def get_quiz(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("student", "teacher", "admin")),
):
    await _get_lesson_or_404(db, lesson_id)

    res = await db.execute(
        select(QuizQuestion)
        .options(selectinload(QuizQuestion.options))
        .where(QuizQuestion.lesson_id == lesson_id)
        .order_by(QuizQuestion.order)
    )
    questions = list(res.scalars().unique().all())

    return questions


@router.post(
    "/lessons/{lesson_id}/quiz/submit",
    response_model=QuizSubmitOut,
)
async def submit_quiz(
    lesson_id: int,
    payload: QuizSubmitIn,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("student", "teacher", "admin")),
):
    res = await db.execute(
        select(QuizQuestion)
        .options(selectinload(QuizQuestion.options))
        .where(QuizQuestion.lesson_id == lesson_id)
        .order_by(QuizQuestion.order)
    )
    questions = list(res.scalars().unique().all())

    if not questions:
        raise HTTPException(status_code=404, detail="Quiz not found")

    total = len(questions)
    score = 0

    for question in questions:
        selected_option_id = payload.answers.get(question.id)
        if not selected_option_id:
            continue

        correct_option = next(
            (option for option in question.options if option.is_correct),
            None,
        )

        if correct_option and correct_option.id == selected_option_id:
            score += 1

    passed = score >= max(1, int(0.7 * total + 0.9999))

    return QuizSubmitOut(score=score, total=total, passed=passed)


# ----------------------------
# ADMIN / TEACHER CRUD
# ----------------------------


@router.get(
    "/lessons/{lesson_id}/quiz/admin",
    response_model=list[QuizQuestionOut],
)
async def get_quiz_admin(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("teacher", "admin")),
):
    await _require_quiz_editor(db, lesson_id, user)

    res = await db.execute(
        select(QuizQuestion)
        .options(selectinload(QuizQuestion.options))
        .where(QuizQuestion.lesson_id == lesson_id)
        .order_by(QuizQuestion.order)
    )
    questions = list(res.scalars().unique().all())
    return questions


@router.post(
    "/lessons/{lesson_id}/quiz/questions",
    response_model=QuizQuestionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_quiz_question(
    lesson_id: int,
    payload: QuizQuestionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("teacher", "admin")),
):
    await _require_quiz_editor(db, lesson_id, user)

    question = QuizQuestion(
        lesson_id=lesson_id,
        question_text=payload.question_text,
        order=payload.order,
    )
    db.add(question)
    await db.commit()

    question = await _get_question_or_404(db, question.id)
    return question


@router.patch(
    "/quiz/questions/{question_id}",
    response_model=QuizQuestionOut,
)
async def update_quiz_question(
    question_id: int,
    payload: QuizQuestionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("teacher", "admin")),
):
    question = await _get_question_or_404(db, question_id)
    await _require_quiz_editor(db, question.lesson_id, user)

    if payload.question_text is not None:
        question.question_text = payload.question_text
    if payload.order is not None:
        question.order = payload.order

    await db.commit()
    question = await _get_question_or_404(db, question_id)
    return question


@router.delete(
    "/quiz/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_quiz_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("teacher", "admin")),
):
    question = await _get_question_or_404(db, question_id)
    await _require_quiz_editor(db, question.lesson_id, user)

    await db.delete(question)
    await db.commit()
    return None


@router.post(
    "/quiz/questions/{question_id}/options",
    response_model=QuizOptionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_quiz_option(
    question_id: int,
    payload: QuizOptionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("teacher", "admin")),
):
    question = await _get_question_or_404(db, question_id)
    await _require_quiz_editor(db, question.lesson_id, user)

    if payload.is_correct:
        res = await db.execute(
            select(QuizOption).where(
                QuizOption.question_id == question_id,
                QuizOption.is_correct.is_(True),
            )
        )
        existing_correct = res.scalar_one_or_none()
        if existing_correct:
            raise HTTPException(
                status_code=400,
                detail="This question already has a correct option",
            )

    option = QuizOption(
        question_id=question_id,
        option_text=payload.option_text,
        is_correct=payload.is_correct,
        order=payload.order,
    )
    db.add(option)
    await db.commit()
    await db.refresh(option)
    return option


@router.patch(
    "/quiz/options/{option_id}",
    response_model=QuizOptionOut,
)
async def update_quiz_option(
    option_id: int,
    payload: QuizOptionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("teacher", "admin")),
):
    option = await _get_option_or_404(db, option_id)

    res = await db.execute(
        select(QuizQuestion).where(QuizQuestion.id == option.question_id)
    )
    question = res.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Quiz question not found")

    await _require_quiz_editor(db, question.lesson_id, user)

    if payload.is_correct is True and option.is_correct is False:
        res = await db.execute(
            select(QuizOption).where(
                QuizOption.question_id == option.question_id,
                QuizOption.is_correct.is_(True),
                QuizOption.id != option.id,
            )
        )
        existing_correct = res.scalar_one_or_none()
        if existing_correct:
            raise HTTPException(
                status_code=400,
                detail="This question already has a correct option",
            )

    if payload.option_text is not None:
        option.option_text = payload.option_text
    if payload.is_correct is not None:
        option.is_correct = payload.is_correct
    if payload.order is not None:
        option.order = payload.order

    await db.commit()
    await db.refresh(option)

    await _ensure_single_correct_option(db, option.question_id)
    return option


@router.delete(
    "/quiz/options/{option_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_quiz_option(
    option_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("teacher", "admin")),
):
    option = await _get_option_or_404(db, option_id)

    res = await db.execute(
        select(QuizQuestion).where(QuizQuestion.id == option.question_id)
    )
    question = res.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Quiz question not found")

    await _require_quiz_editor(db, question.lesson_id, user)

    deleting_correct = option.is_correct
    question_id = option.question_id

    await db.delete(option)
    await db.commit()

    if deleting_correct:
        res = await db.execute(
            select(QuizOption).where(QuizOption.question_id == question_id)
        )
        remaining_options = list(res.scalars().all())
        if remaining_options:
            raise HTTPException(
                status_code=400,
                detail="You deleted the correct option. Please set another correct option.",
            )

    return None
