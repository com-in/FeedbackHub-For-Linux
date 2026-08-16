"""反馈中心入口：python -m feedbackhub"""
import sys

from .app import run


def main():
    sys.exit(run())


if __name__ == "__main__":
    main()