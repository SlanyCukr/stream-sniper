import Select from 'react-select'

interface CreatorOption {
    label: string
    value: number
}

interface CreatorFilterProps {
    creators: CreatorOption[]
    value: CreatorOption | null
    onChange: (option: CreatorOption | null) => void
}

const CreatorFilter = ({
    creators,
    value,
    onChange,
}: CreatorFilterProps) => (
    <div className="toolbar-field">
        <label
            htmlFor="creator-select"
            className="visually-hidden">
            Filter by creator
        </label>
        <Select
            classNamePrefix="rs"
            instanceId="creator-select"
            inputId="creator-select"
            options={creators}
            value={value}
            onChange={option => onChange((option as CreatorOption | null) ?? null)}
            placeholder="All creators"
            isClearable
            aria-label="Filter streams by creator"
            aria-describedby="creator-help"
        />
        <div
            id="creator-help"
            className="visually-hidden">
            Choose a specific creator to filter streams, or leave empty to show all streams
        </div>
    </div>
)

export default CreatorFilter
