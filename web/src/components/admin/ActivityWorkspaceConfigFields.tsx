/**
 * ActivityWorkspaceConfigFields — admin configuration of what a programme or
 * hackathon workspace expects from each participant.
 *
 * Everything configured here is *individual*: the objectives, instructions,
 * requirements, resources, task checklist and the deliverable parts are shown
 * in each participant's own workspace, and each participant tracks their own
 * task completion.
 */

import { FormField } from '../form/FormField'
import { TextInput } from '../form/TextInput'
import { Textarea } from '../form/Textarea'
import { Checkbox } from '../form/Checkbox'
import {
  REQUIRED_DELIVERABLE_LABELS,
  REQUIRED_DELIVERABLE_OPTIONS,
} from '../../types/activity'
import type {
  ActivityResource,
  ActivityTask,
  RequiredDeliverable,
} from '../../types/activity'

export interface ActivityWorkspaceConfigValues {
  objectives: string
  instructions: string
  requirements: string
  resources: ActivityResource[]
  tasks: ActivityTask[]
  required_deliverables: RequiredDeliverable[]
}

export interface ActivityWorkspaceConfigFieldsProps {
  values: ActivityWorkspaceConfigValues
  onChange: (values: ActivityWorkspaceConfigValues) => void
  disabled?: boolean
}

function newTaskId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `task-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

export function ActivityWorkspaceConfigFields({
  values,
  onChange,
  disabled = false,
}: ActivityWorkspaceConfigFieldsProps) {
  function patch(next: Partial<ActivityWorkspaceConfigValues>): void {
    onChange({ ...values, ...next })
  }

  function patchResource(index: number, next: Partial<ActivityResource>): void {
    patch({
      resources: values.resources.map((resource, i) =>
        i === index ? { ...resource, ...next } : resource,
      ),
    })
  }

  function patchTask(index: number, next: Partial<ActivityTask>): void {
    patch({
      tasks: values.tasks.map((task, i) => (i === index ? { ...task, ...next } : task)),
    })
  }

  function toggleDeliverable(part: RequiredDeliverable): void {
    const current = values.required_deliverables
    patch({
      required_deliverables: current.includes(part)
        ? current.filter((item) => item !== part)
        : [...current, part],
    })
  }

  return (
    <>
      <FormField
        id="activity-objectives"
        label="Objectives"
        hint="One per line"
      >
        <Textarea
          id="activity-objectives"
          rows={4}
          value={values.objectives}
          disabled={disabled}
          onChange={(value) => patch({ objectives: value })}
          placeholder={'Ship a working prototype\nPresent your findings'}
        />
      </FormField>

      <FormField id="activity-instructions" label="Instructions">
        <Textarea
          id="activity-instructions"
          rows={5}
          value={values.instructions}
          disabled={disabled}
          onChange={(value) => patch({ instructions: value })}
          placeholder="How should participants approach this activity?"
        />
      </FormField>

      <FormField id="activity-requirements" label="Requirements" hint="One per line">
        <Textarea
          id="activity-requirements"
          rows={4}
          value={values.requirements}
          disabled={disabled}
          onChange={(value) => patch({ requirements: value })}
          placeholder={'A public repository\nA 3-minute demo video'}
        />
      </FormField>

      <div className="admin-section__field">
        <p className="form-field__label">Required deliverable parts</p>
        <p className="admin-section__hint">
          Participants must provide every part you tick before their deliverable is accepted.
        </p>
        <div className="workspace__required">
          {REQUIRED_DELIVERABLE_OPTIONS.map((part) => (
            <Checkbox
              key={part}
              id={`activity-deliverable-${part}`}
              label={REQUIRED_DELIVERABLE_LABELS[part]}
              checked={values.required_deliverables.includes(part)}
              disabled={disabled}
              onChange={() => toggleDeliverable(part)}
            />
          ))}
        </div>
      </div>

      <div className="admin-section__field">
        <div className="admin-section__head">
          <p className="form-field__label">Resources</p>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            disabled={disabled}
            onClick={() =>
              patch({ resources: [...values.resources, { label: '', url: '' }] })
            }
          >
            Add resource
          </button>
        </div>
        {values.resources.length === 0 ? (
          <p className="admin-section__hint">No resources linked yet.</p>
        ) : null}
        {values.resources.map((resource, index) => (
          <div className="admin-form__row" key={`resource-${index}`}>
            <FormField id={`activity-resource-label-${index}`} label="Label">
              <TextInput
                id={`activity-resource-label-${index}`}
                value={resource.label}
                disabled={disabled}
                onChange={(value) => patchResource(index, { label: value })}
                placeholder="Starter repo"
              />
            </FormField>
            <FormField id={`activity-resource-url-${index}`} label="URL">
              <TextInput
                id={`activity-resource-url-${index}`}
                value={resource.url}
                inputMode="url"
                disabled={disabled}
                onChange={(value) => patchResource(index, { url: value })}
                placeholder="https://github.com/…"
              />
            </FormField>
            <div className="admin-table__actions">
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                disabled={disabled}
                onClick={() =>
                  patch({
                    resources: values.resources.filter((_, i) => i !== index),
                  })
                }
              >
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="admin-section__field">
        <div className="admin-section__head">
          <p className="form-field__label">Participant checklist</p>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            disabled={disabled}
            onClick={() =>
              patch({
                tasks: [
                  ...values.tasks,
                  { id: newTaskId(), title: '', description: '', due_date: null },
                ],
              })
            }
          >
            Add task
          </button>
        </div>
        <p className="admin-section__hint">
          Each participant ticks these off in their own workspace.
        </p>
        {values.tasks.length === 0 ? (
          <p className="admin-section__hint">No tasks yet.</p>
        ) : null}
        {values.tasks.map((task, index) => (
          <div className="admin-form__row" key={task.id}>
            <FormField id={`activity-task-title-${index}`} label="Task">
              <TextInput
                id={`activity-task-title-${index}`}
                value={task.title}
                disabled={disabled}
                onChange={(value) => patchTask(index, { title: value })}
                placeholder="Build the prototype"
              />
            </FormField>
            <FormField id={`activity-task-due-${index}`} label="Due date">
              <TextInput
                id={`activity-task-due-${index}`}
                type="date"
                value={task.due_date ?? ''}
                disabled={disabled}
                onChange={(value) => patchTask(index, { due_date: value || null })}
              />
            </FormField>
            <div className="admin-table__actions">
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                disabled={disabled}
                onClick={() => patch({ tasks: values.tasks.filter((_, i) => i !== index) })}
              >
                Remove
              </button>
            </div>
            <FormField id={`activity-task-description-${index}`} label="Description">
              <Textarea
                id={`activity-task-description-${index}`}
                rows={2}
                value={task.description}
                disabled={disabled}
                onChange={(value) => patchTask(index, { description: value })}
              />
            </FormField>
          </div>
        ))}
      </div>
    </>
  )
}
