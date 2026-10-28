/**
 * ActivityTaskChecklist — the member's personal task checklist.
 *
 * Each task belongs to the activity; the completion flag is stored per member
 * (there is no shared/team state — participation is individual).
 */

import { useState } from 'react'
import type { ActivityTask } from '../../types/activitySubmission'

export interface ActivityTaskChecklistProps {
  tasks: ActivityTask[]
  busyTaskId?: string | null
  onToggle: (taskId: string, completed: boolean) => void
}

function formatDueDate(value: string | null): string | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function ActivityTaskChecklist({ tasks, busyTaskId = null, onToggle }: ActivityTaskChecklistProps) {
  const [pendingId, setPendingId] = useState<string | null>(null)

  if (tasks.length === 0) return null

  function handleToggle(task: ActivityTask): void {
    setPendingId(task.id)
    onToggle(task.id, !task.completed)
  }

  return (
    <ul className="workspace__tasks">
      {tasks.map((task) => {
        const busy = busyTaskId === task.id || pendingId === task.id
        const due = formatDueDate(task.due_date)
        return (
          <li key={task.id} className="workspace__task" data-completed={task.completed}>
            <input
              type="checkbox"
              id={`activity-task-${task.id}`}
              checked={task.completed}
              disabled={busy}
              onChange={() => handleToggle(task)}
            />
            <div className="workspace__task-body">
              <label className="workspace__task-title" htmlFor={`activity-task-${task.id}`}>
                {task.title}
              </label>
              {task.description ? (
                <p className="workspace__task-desc">{task.description}</p>
              ) : null}
              {due ? <span className="workspace__task-due">Due {due}</span> : null}
            </div>
          </li>
        )
      })}
    </ul>
  )
}
