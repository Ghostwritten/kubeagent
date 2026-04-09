"""Allow running kubeagent as: python -m kubeagent"""

from kubeagent.cli.main import cli

if __name__ == "__main__":
    cli()
