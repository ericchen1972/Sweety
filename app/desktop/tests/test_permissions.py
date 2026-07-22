from sweety_app.permissions import _automation_script, check_automation_permissions


def test_automation_scripts_use_actions_that_trigger_macos_consent():
    assert _automation_script("jp.naver.line.mac") == 'tell application id "jp.naver.line.mac" to activate'
    assert _automation_script("com.apple.systemevents") == (
        'tell application id "com.apple.systemevents" to keystroke ""'
    )


def test_automation_check_requests_system_events_and_line_from_native_probe():
    calls = []

    def probe(bundle_id: str, prompt: bool) -> bool:
        calls.append((bundle_id, prompt))
        return True

    status = check_automation_permissions(prompt=True, probe=probe)

    assert status.system_events is True
    assert status.line is True
    assert status.ready is True
    assert calls == [
        ("com.apple.systemevents", True),
        ("jp.naver.line.mac", True),
    ]


def test_automation_check_keeps_each_target_result():
    status = check_automation_permissions(
        prompt=False,
        probe=lambda bundle_id, _prompt: bundle_id == "com.apple.systemevents",
    )

    assert status.system_events is True
    assert status.line is False
    assert status.ready is False
    assert status.missing == ("LINE",)


def test_automation_check_attempts_both_targets_after_first_denial():
    calls = []

    def probe(bundle_id: str, _prompt: bool) -> bool:
        calls.append(bundle_id)
        return bundle_id == "jp.naver.line.mac"

    status = check_automation_permissions(prompt=True, probe=probe)

    assert status.ready is False
    assert calls == ["com.apple.systemevents", "jp.naver.line.mac"]
