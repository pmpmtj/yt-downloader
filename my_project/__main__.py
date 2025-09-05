# __main_.py
def main():
    from .core_CLI import main as cli_main
    from dotenv import load_dotenv
    from pathlib import Path
    
    # Look for .env file in parent directories
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Fallback to default behavior
        load_dotenv()
    
    cli_main()

if __name__ == "__main__":
    main()