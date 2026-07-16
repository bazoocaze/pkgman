import pytest
from managers import Manager


def test_apt_install_command():
    m = Manager("apt")
    assert m._build_cmd("install", "git") == ["apt", "install", "-y", "git"]


def test_apt_remove_command():
    m = Manager("apt")
    assert m._build_cmd("remove", "git") == ["apt", "remove", "-y", "git"]


def test_yum_install_command():
    m = Manager("yum")
    assert m._build_cmd("install", "git") == ["yum", "install", "-y", "git"]


def test_brew_install_command():
    m = Manager("brew")
    assert m._build_cmd("install", "git") == ["brew", "install", "git"]


def test_brew_uninstall_command():
    m = Manager("brew")
    assert m._build_cmd("remove", "git") == ["brew", "uninstall", "git"]


def test_sudo_prefix():
    cmd = ["sudo"] + ["apt", "install", "-y", "git"]
    assert cmd == ["sudo", "apt", "install", "-y", "git"]


def test_unknown_manager_raises():
    m = Manager("nope")
    with pytest.raises(RuntimeError, match="Unknown manager"):
        m._build_cmd("install", "x")
