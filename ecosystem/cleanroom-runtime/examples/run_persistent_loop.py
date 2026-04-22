from arc_kernel.engine import KernelEngine
from lucifer_runtime.runtime import LuciferRuntime
from cognition_services.goal_engine import GoalEngine
from cognition_services.persistent_loop import PersistentLoop


def main() -> None:
    runtime = LuciferRuntime(KernelEngine())
    goals = GoalEngine()
    goals.add_goal("list the current files", priority=80, completion_criteria=["read command executed"])
    loop = PersistentLoop(goal_engine=goals)
    tick = loop.tick(runtime)
    print(tick)


if __name__ == "__main__":
    main()
