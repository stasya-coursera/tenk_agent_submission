#!/usr/bin/env python3
"""
Debug script to run multiple questions through the CLI.
"""

import sys
import time
import asyncio
from cli import _run_single_query

# Define your questions here
QUESTIONS = [
    # "What day is it today?",
    # "What's Apple's current stock price?",
    # "How does Apple's P/E ratio compare to Microsoft?"
    # "What are Apple's risk factors?"
    "What are Apple's top 3 risk factors mentioned in their latest 10-K, and what percentage of total revenue did they spend on R&D?",
    "How does Apple's gross margin compare to Microsoft's current gross margin, and what reasons does Apple cite in their 10-K for any margin pressure?",
]

async def run_questions_async(questions=None, start_from=0):
    """Run a list of questions through the CLI asynchronously.
    
    Args:
        questions: List of questions to run. If None, uses QUESTIONS.
        start_from: Index to start from (useful if you want to skip some questions).
    """
    if questions is None:
        questions = QUESTIONS
    
    print(f"🚀 Running {len(questions)} questions starting from index {start_from}...")
    print("=" * 80)
    
    for i, question in enumerate(questions[start_from:], start_from):
        print(f"\n📝 Question {i+1}/{len(questions)}: {question}")
        print("-" * 80)
        
        try:
            # Run the query directly
            answer = await _run_single_query(question)
            print(f"💡 Answer: {answer}")
        except Exception as e:
            print(f"❌ Error running question {i+1}: {e}")
            continue
        
        print("\n" + "=" * 80)
        
        # Add a small delay between questions
        await asyncio.sleep(1)
    
    print("✅ All questions completed!")

def run_questions(questions=None, start_from=0):
    """Sync wrapper for run_questions_async."""
    asyncio.run(run_questions_async(questions, start_from))

async def run_single_question_async(index):
    """Run a single question by index asynchronously.
    
    Args:
        index: 0-based index of the question to run.
    """
    if index >= len(QUESTIONS):
        print(f"❌ Question index {index} is out of range. Available: 0-{len(QUESTIONS)-1}")
        return
    
    question = QUESTIONS[index]
    print(f"📝 Running question {index+1}: {question}")
    print("-" * 80)
    
    try:
        answer = await _run_single_query(question)
        print(f"💡 Answer: {answer}")
    except Exception as e:
        print(f"❌ Error running question: {e}")

def run_single_question(index):
    """Sync wrapper for run_single_question_async."""
    asyncio.run(run_single_question_async(index))

if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) == 1:
        # Run all questions
        run_questions()
    elif len(sys.argv) == 2:
        arg = sys.argv[1]
        if arg == "--help" or arg == "-h":
            print("Usage:")
            print("  python debug_cli_questions.py              # Run all questions")
            print("  python debug_cli_questions.py <index>      # Run single question by index (0-based)")
            print("  python debug_cli_questions.py <start> <end> # Run questions from start to end index")
            print("\nAvailable questions:")
            for i, q in enumerate(QUESTIONS):
                print(f"  {i}: {q}")
        else:
            # Run single question by index
            try:
                index = int(arg)
                run_single_question(index)
            except ValueError:
                print(f"❌ Invalid index: {arg}")
                print("Use --help for usage information")
    elif len(sys.argv) == 3:
        # Run questions from start to end index
        try:
            start = int(sys.argv[1])
            end = int(sys.argv[2])
            if end > len(QUESTIONS):
                end = len(QUESTIONS)
            questions_slice = QUESTIONS[start:end]
            run_questions(questions_slice, start_from=start)
        except ValueError:
            print("❌ Invalid start/end indices")
            print("Use --help for usage information")
