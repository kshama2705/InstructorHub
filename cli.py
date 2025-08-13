import argparse, json, sys
from metric_registry import MetricRegistry
from executor import execute_metric
from feedback import module_feedback, course_feedback
from llama_intent_parser import parse_question_with_fallback

def main():
    parser = argparse.ArgumentParser(description="Instructor metrics CLI (user data)")
    parser.add_argument("--db", type=str, default="user.db", help="Path to SQLite DB")
    parser.add_argument("--metrics", type=str, default="metrics.json", help="Metrics registry JSON")

    subparsers = parser.add_subparsers(dest='command')

    # Metrics Q&A
    msp = subparsers.add_parser('ask', help='Ask numeric metric questions')
    msp.add_argument('question', type=str, help='Natural language question for metrics')
    # LLaMA is ON by default; you can force rules-only:
    msp.add_argument("--rules-only", action="store_true", help="Disable LLaMA; use rules parser only")

    # Feedback analysis
    fsp = subparsers.add_parser('feedback-module', help='Module-level feedback')
    fsp.add_argument('module_id', type=int, help='Module ID')

    cfsp = subparsers.add_parser('feedback-course', help='Course-level feedback')

    args = parser.parse_args()

    if args.command == 'ask':
        registry = MetricRegistry(args.metrics)

        if args.rules_only:
            from intent_parser import parse_question as rules_parse
            intent = rules_parse(args.question)
        else:
            intent = parse_question_with_fallback(args.question, registry, args.db)

        if not intent:
            tip = (
                "Could not understand the question.\n"
                "Tips:\n"
                "  • Try including IDs like 'module 2' or names like 'module Foundations of Education'\n"
                "  • Use --rules-only to bypass LLaMA if your endpoint isn’t configured"
            )
            print(tip, file=sys.stderr)
            sys.exit(2)

        sql, params = registry.render(intent["metric"], intent["params"])
        value = execute_metric(args.db, sql, params)
        if value is None:
            print("No result.", file=sys.stderr)
            sys.exit(1)

        print(value)
        print(json.dumps({"metric": intent["metric"], "params": params}, indent=2), file=sys.stderr)

    elif args.command == 'feedback-module':
        out = module_feedback(args.db, args.module_id)
        print(json.dumps(out, indent=2))

    elif args.command == 'feedback-course':
        out = course_feedback(args.db)
        print(json.dumps(out, indent=2))

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
