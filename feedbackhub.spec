Name:           feedbackhub
Version:        1.0.0
Release:        1%{?dist}
Summary:        A local app for the Linux Feedback Hub

License:        GPL-3.0-or-later
URL:            https://github.com/com-in/FeedbackHub-For-Linux
Source0:        feedbackhub-%{version}.tar.gz

BuildArch:      noarch
Requires:       python3, python3-gobject, gtk3

%description
A GTK3 application for the Linux Feedback Hub. All feedback data
is stored locally; nothing is uploaded. Built with Python 3 and GTK 3.

%prep
%setup -q -n feedbackhub-%{version}

%build
# 纯 Python/GTK 应用，无需编译。
:

%install
rm -rf %{buildroot}
# 启动脚本（指向已安装的包目录）
cat > %{buildroot}.launcher <<'LAUNCHER'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/usr/share/feedbackhub')
from feedbackhub.app import run
sys.exit(run())
LAUNCHER
install -Dm755 %{buildroot}.launcher %{buildroot}%{_bindir}/feedbackhub
rm -f %{buildroot}.launcher
# Python 包
install -d %{buildroot}%{_datadir}/feedbackhub
cp -r feedbackhub %{buildroot}%{_datadir}/feedbackhub/
find %{buildroot}%{_datadir}/feedbackhub -name '__pycache__' -type d -prune -exec rm -rf {} +
find %{buildroot}%{_datadir}/feedbackhub -name '*.pyc' -delete
# 桌面文件
install -Dm644 feedbackhub.desktop %{buildroot}%{_datadir}/applications/feedbackhub.desktop
# 图标
install -Dm644 feedbackhub/assets/icon.svg \
  %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/feedbackhub.svg

%files
%{_bindir}/feedbackhub
%{_datadir}/feedbackhub/feedbackhub/*.py
%{_datadir}/feedbackhub/feedbackhub/styles.css
%{_datadir}/feedbackhub/feedbackhub/assets/icon.svg
%{_datadir}/applications/feedbackhub.desktop
%{_datadir}/icons/hicolor/scalable/apps/feedbackhub.svg

%changelog
* Wed Aug 2026 Feedback Hub Maintainers <maintainer@example.local> - 1.0.0-1
- Initial release