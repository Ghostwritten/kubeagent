class Kubeagent < Formula
  include Language::Python::Virtualenv

  desc "Natural language CLI for Kubernetes cluster management"
  homepage "https://github.com/Ghostwritten/kubeagent"
  url "https://pypi.io/packages/source/k/kubeagent-cli/kubeagent_cli-VERSION.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "kubeagent", shell_output("#{bin}/kubeagent --version")
  end
end
