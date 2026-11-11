import { useEffect, useMemo } from "react";
import { observer } from "mobx-react";
import { Button } from "@humansignal/ui";
import { CaretLeftIcon, CaretRightIcon } from "@humansignal/icons";
import { cn } from "../../utils/bem";
import { guidGenerator } from "../../utils/unique";
import { Hotkey } from "../../core/Hotkey";
import "./CurrentTask.prefix.css";

export const CurrentTask = observer(({ store }) => {
  useEffect(() => {
    store.commentStore.setAddedCommentThisSession(false);
  }, []);

  const historyEnabled = store.hasInterface("topbar:prevnext");
  const showCounter = store.hasInterface("topbar:task-counter");

  // Single source of truth for the next button, shared with the task:next
  // hotkey in AppStore so keyboard and mouse behave identically.
  const { canNavigateNext, canPostponeTask, requiresAnnotationSubmission, canSkipOrPostpone } =
    store.nextButtonState;

  // Memoized messages for previous button
  const prevButtonMessage = useMemo(() => {
    return !store.canGoPrevTask ? "No previous task" : "Previous task";
  }, [store.canGoPrevTask]);

  // Memoized messages for next button
  const nextButtonMessage = useMemo(() => {
    if (requiresAnnotationSubmission) {
      return "Submit an annotation to continue";
    }
    if (canNavigateNext) {
      return "Next task";
    }
    if (canPostponeTask) {
      return "Postpone task";
    }
    if (!canSkipOrPostpone) {
      return "Cannot postpone: task cannot be skipped";
    }
    return "No next task available";
  }, [requiresAnnotationSubmission, canNavigateNext, canPostponeTask, canSkipOrPostpone]);

  return (
    <div className={cn("bottombar").elem("section").toClassName()}>
      <div className={cn("current-task").mod({ "with-history": historyEnabled }).toClassName()}>
        <div className={cn("current-task").elem("task-id").toClassName()}>
          {store.task.id ?? guidGenerator()}
          {historyEnabled && showCounter && (
            <div className={cn("current-task").elem("task-count").toClassName()}>
              {store.queuePosition} of {store.queueTotal}
            </div>
          )}
        </div>
        {historyEnabled && (
          <div className={cn("current-task").elem("history-controls").mod({ newui: true }).toClassName()}>
            <Hotkey.Tooltip name="task:prev" title={prevButtonMessage}>
              <Button
                data-testid="prev-task"
                aria-label={prevButtonMessage}
                look="string"
                disabled={!historyEnabled || !store.canGoPrevTask}
                onClick={store.prevTask}
                variant="neutral"
                leading={<CaretLeftIcon size={24} />}
                size="small"
              />
            </Hotkey.Tooltip>
            <Hotkey.Tooltip name="task:next" title={nextButtonMessage}>
              <Button
                data-testid="next-task"
                aria-label={nextButtonMessage}
                look="string"
                disabled={!canNavigateNext && !canPostponeTask}
                onClick={store.nextOrPostpone}
                variant={!canNavigateNext && canPostponeTask ? "primary" : "neutral"}
                leading={<CaretRightIcon size={24} />}
                size="small"
              />
            </Hotkey.Tooltip>
          </div>
        )}
      </div>
    </div>
  );
});
