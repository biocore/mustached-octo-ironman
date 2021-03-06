./scripts/moi submit --user=ci-test-py --cmd="return 42"
./scripts/moi submit --user=ci-test-py --cmd="float('crash and burn')"
./scripts/moi submit --user=ci-test-sys --cmd="echo 42" --cmd-type=system
./scripts/moi submit --user=ci-test-sys --cmd="crash-and-burn" --cmd-type=system

py_fail_count=$(./scripts/moi userjobs --key=ci-test-py --summary | grep -c Failed)
py_win_count=$(./scripts/moi userjobs --key=ci-test-py --summary | grep -c Success)
sys_fail_count=$(./scripts/moi userjobs --key=ci-test-sys --summary | grep -c Failed)
sys_win_count=$(./scripts/moi userjobs --key=ci-test-sys --summary | grep -c Success)

if [ $py_fail_count -ne 1 ] || [ $py_win_count -ne 1 ] || [ $sys_fail_count -ne 1 ] || [ $sys_win_count -ne 1 ]
then
    false
fi
