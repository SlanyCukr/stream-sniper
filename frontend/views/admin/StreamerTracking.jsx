'use client'
import {
    useState, useEffect, useCallback,
} from 'react'
import {
    Card, Table, Button, Alert, Spinner, Modal, Form, Pagination,
} from 'react-bootstrap'
import { api, retrieveTwitchChannelSearch } from '@/lib/api'
import AsyncSearchSelect from '@/components/AsyncSearchSelect'

const StreamerTracking = () => {
    const [
        streamers,
        setStreamers,
    ] = useState([
    ])
    const [
        loading,
        setLoading,
    ] = useState(true)
    const [
        error,
        setError,
    ] = useState(null)
    const [
        success,
        setSuccess,
    ] = useState(null)
    const [
        showAddModal,
        setShowAddModal,
    ] = useState(false)
    const [
        removeTarget,
        setRemoveTarget,
    ] = useState(null)
    const [
        pagination,
        setPagination,
    ] = useState({
        offset: 0,
        limit: 20,
        total: 0,
        currentPage: 1,
    })
    const [
        filters,
        setFilters,
    ] = useState({
        is_active: null,
        processing_enabled: null,
    })
    const [
        newStreamer,
        setNewStreamer,
    ] = useState({
        twitch_username: '',
        notes: '',
        is_active: true,
        processing_enabled: true,
    })
    const [
        formSubmitting,
        setFormSubmitting,
    ] = useState(false)

    const fetchStreamers = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)

            const params = new URLSearchParams({
                offset: pagination.offset.toString(),
                limit: pagination.limit.toString(),
            })

            if (filters.is_active !== null) {
                params.append('is_active', filters.is_active.toString())
            }
            if (filters.processing_enabled !== null) {
                params.append('processing_enabled', filters.processing_enabled.toString())
            }

            const { data } = await api.get(`/admin/tracking/streamers?${params}`)
            setStreamers(data.streamers)
            setPagination(prev => ({
                ...prev,
                total: data.total,
                currentPage: Math.floor(data.offset / data.limit) + 1,
            }))
        } catch (fetchError) {
            console.error('Error fetching streamers:', fetchError)
            setError(fetchError.response?.data?.detail || fetchError.message || 'Failed to fetch streamers')
        } finally {
            setLoading(false)
        }
    }, [
        pagination.offset,
        pagination.limit,
        filters,
    ])

    useEffect(() => {
        fetchStreamers()
    }, [
        fetchStreamers,
    ])

    const handleAddStreamer = async e => {
        e.preventDefault()
        try {
            setFormSubmitting(true)
            setError(null)

            await api.post('/admin/tracking/streamers', newStreamer)
            setSuccess('Streamer added successfully')
            setShowAddModal(false)
            setNewStreamer({
                twitch_username: '',
                notes: '',
                is_active: true,
                processing_enabled: true,
            })
            fetchStreamers()
        } catch (addError) {
            console.error('Error adding streamer:', addError)
            setError(addError.response?.data?.detail || addError.message || 'Failed to add streamer')
        } finally {
            setFormSubmitting(false)
        }
    }

    /**
     * Search live Twitch channels for the add-streamer typeahead.
     * @param {string} query
     * @returns {Promise<Array<{value: string, label: string}>>}
     */
    const loadChannelOptions = useCallback(async query => {
        const trimmed = query.trim()
        if (trimmed.length < 2) {
            return []
        }
        try {
            const { data } = await retrieveTwitchChannelSearch(trimmed)
            return (data || []).map(channel => ({
                value: channel.login,
                label: channel.display_name
                    ? `${channel.display_name} (${channel.login})`
                    : channel.login,
            }))
        } catch {
            return []
        }
    }, [
    ])

    const handleToggleActive = async (streamerId, currentStatus) => {
        try {
            await api.put(`/admin/tracking/streamers/${streamerId}`, {
                is_active: !currentStatus,
            })
            setSuccess('Streamer updated successfully')
            fetchStreamers()
        } catch (activeError) {
            console.error('Error updating streamer:', activeError)
            setError(activeError.response?.data?.detail || activeError.message || 'Failed to update streamer')
        }
    }

    const handleToggleProcessing = async (streamerId, currentStatus) => {
        try {
            await api.put(`/admin/tracking/streamers/${streamerId}`, {
                processing_enabled: !currentStatus,
            })
            setSuccess('Streamer updated successfully')
            fetchStreamers()
        } catch (toggleError) {
            console.error('Error updating streamer:', toggleError)
            setError(toggleError.response?.data?.detail || toggleError.message || 'Failed to update streamer')
        }
    }

    const handleRemoveStreamer = async streamerId => {
        try {
            await api.delete(`/admin/tracking/streamers/${streamerId}`)
            setSuccess('Streamer removed successfully')
            fetchStreamers()
        } catch (removeError) {
            console.error('Error removing streamer:', removeError)
            setError(removeError.response?.data?.detail || removeError.message || 'Failed to remove streamer')
        } finally {
            setRemoveTarget(null)
        }
    }

    const handlePageChange = page => {
        setPagination(prev => ({
            ...prev,
            offset: (page - 1) * prev.limit,
            currentPage: page,
        }))
    }

    const formatDateTime = dateString => {
        if (!dateString) {
            return 'Never'
        }
        return new Date(dateString).toLocaleString()
    }

    const getStatusChip = isActive => isActive ?
        <span className="status-chip is-ok">Active</span> :
        <span className="status-chip is-err">Inactive</span>

    const getProcessingChip = isEnabled => isEnabled ?
        <span className="status-chip is-ok">Enabled</span> :
        <span className="status-chip is-warn">Disabled</span>

    const totalPages = Math.ceil(pagination.total / pagination.limit)

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Streamer tracking</h1>
                    <p className="page-sub">Automated VOD collection targets</p>
                </div>
                <div className="page-actions">
                    <Button
                        variant="primary"
                        onClick={() => setShowAddModal(true)}
                        disabled={loading}
                    >
                        <i
                            className="bi bi-plus-circle me-2"
                            aria-hidden="true" />
                        Add streamer
                    </Button>
                </div>
            </div>

            {error && (
                <Alert
                    variant="danger"
                    className="mb-4"
                    dismissible
                    onClose={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {success && (
                <Alert
                    variant="success"
                    className="mb-4"
                    dismissible
                    onClose={() => setSuccess(null)}>
                    {success}
                </Alert>
            )}

            <div className="toolbar">
                <span
                    className="toolbar-label"
                    aria-hidden="true">
                    Filter
                </span>
                <div className="toolbar-field">
                    <label
                        htmlFor="tracking-status-filter"
                        className="visually-hidden"
                    >
                        Filter by status
                    </label>
                    <Form.Select
                        id="tracking-status-filter"
                        value={filters.is_active === null ? '' : filters.is_active.toString()}
                        onChange={e => setFilters(prev => ({
                            ...prev,
                            is_active: e.target.value === '' ? null : e.target.value === 'true',
                        }))}
                    >
                        <option value="">All statuses</option>
                        <option value="true">Active</option>
                        <option value="false">Inactive</option>
                    </Form.Select>
                </div>
                <div className="toolbar-field">
                    <label
                        htmlFor="tracking-processing-filter"
                        className="visually-hidden"
                    >
                        Filter by processing
                    </label>
                    <Form.Select
                        id="tracking-processing-filter"
                        value={filters.processing_enabled === null ? '' : filters.processing_enabled.toString()}
                        onChange={e => setFilters(prev => ({
                            ...prev,
                            processing_enabled: e.target.value === '' ? null : e.target.value === 'true',
                        }))}
                    >
                        <option value="">All processing</option>
                        <option value="true">Processing enabled</option>
                        <option value="false">Processing disabled</option>
                    </Form.Select>
                </div>
                <span className="toolbar-readout">
                    {pagination.total} tracked
                </span>
            </div>

            <Card>
                <Card.Body className={!loading && streamers.length === 0 ? 'p-0' : ''}>
                    {loading ? (
                        <div className="text-center py-5">
                            <Spinner
                                animation="border"
                                variant="primary" />
                        </div>
                    ) : streamers.length === 0 ? (
                        <div className="empty-state">
                            <div
                                className="empty-scope"
                                aria-hidden="true" />
                            <p className="empty-title">No tracked streamers</p>
                            <p className="empty-hint">
                                No streamers match this filter. Add a streamer to start automated VOD collection.
                            </p>
                        </div>
                    ) : (
                        <>
                            <Table
                                hover
                                responsive>
                                <thead>
                                    <tr>
                                        <th>Username</th>
                                        <th>Display Name</th>
                                        <th>Status</th>
                                        <th>Processing</th>
                                        <th>Last Check</th>
                                        <th>Created</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {streamers.map(streamer => (
                                        <tr key={streamer.id}>
                                            <td>
                                                <strong>{streamer.twitch_username}</strong>
                                            </td>
                                            <td>{streamer.display_name}</td>
                                            <td>{getStatusChip(streamer.is_active)}</td>
                                            <td>{getProcessingChip(streamer.processing_enabled)}</td>
                                            <td className="mono">{formatDateTime(streamer.last_stream_check)}</td>
                                            <td className="mono">{formatDateTime(streamer.created_at)}</td>
                                            <td>
                                                <Button
                                                    variant="outline-primary"
                                                    size="sm"
                                                    className="me-2"
                                                    onClick={() => handleToggleActive(streamer.id, streamer.is_active)}
                                                >
                                                    {streamer.is_active ? 'Deactivate' : 'Activate'}
                                                </Button>
                                                <Button
                                                    variant="outline-primary"
                                                    size="sm"
                                                    className="me-2"
                                                    onClick={() => handleToggleProcessing(streamer.id, streamer.processing_enabled)}
                                                >
                                                    {streamer.processing_enabled ? 'Disable' : 'Enable'}
                                                </Button>
                                                <Button
                                                    variant="outline-danger"
                                                    size="sm"
                                                    onClick={() => setRemoveTarget(streamer)}
                                                >
                                                    Remove
                                                </Button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </Table>

                            <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mt-3">
                                <span className="mono small text-muted">
                                    Showing {streamers.length} of {pagination.total}
                                </span>
                                {totalPages > 1 && (
                                    <Pagination className="mb-0">
                                        <Pagination.First
                                            onClick={() => handlePageChange(1)}
                                            disabled={pagination.currentPage === 1}
                                        />
                                        <Pagination.Prev
                                            onClick={() => handlePageChange(pagination.currentPage - 1)}
                                            disabled={pagination.currentPage === 1}
                                        />
                                        {[
                                            ...Array(Math.min(5, totalPages)),
                                        ].map((_, i) => {
                                            const page = Math.max(1, pagination.currentPage - 2) + i
                                            if (page <= totalPages) {
                                                return (
                                                    <Pagination.Item
                                                        key={page}
                                                        active={page === pagination.currentPage}
                                                        onClick={() => handlePageChange(page)}
                                                    >
                                                        {page}
                                                    </Pagination.Item>
                                                )
                                            }
                                            return null
                                        })}
                                        <Pagination.Next
                                            onClick={() => handlePageChange(pagination.currentPage + 1)}
                                            disabled={pagination.currentPage === totalPages}
                                        />
                                        <Pagination.Last
                                            onClick={() => handlePageChange(totalPages)}
                                            disabled={pagination.currentPage === totalPages}
                                        />
                                    </Pagination>
                                )}
                            </div>
                        </>
                    )}
                </Card.Body>
            </Card>

            {/* Add Streamer Modal */}
            <Modal
                show={showAddModal}
                onHide={() => setShowAddModal(false)}>
                <Modal.Header closeButton>
                    <Modal.Title>Add Streamer to Tracking</Modal.Title>
                </Modal.Header>
                <Form onSubmit={handleAddStreamer}>
                    <Modal.Body>
                        <Form.Group className="mb-3">
                            <Form.Label htmlFor="add-streamer-username">Twitch Username *</Form.Label>
                            <AsyncSearchSelect
                                creatable
                                instanceId="add-streamer-username-select"
                                inputId="add-streamer-username"
                                loadOptions={loadChannelOptions}
                                value={newStreamer.twitch_username
                                    ? {
                                        value: newStreamer.twitch_username,
                                        label: newStreamer.twitch_username,
                                    }
                                    : null}
                                onChange={option => setNewStreamer(prev => ({
                                    ...prev,
                                    twitch_username: option?.value ?? '',
                                }))}
                                placeholder="Search Twitch or type a username"
                                formatCreateLabel={value => `Track "${value}"`}
                                isClearable
                            />
                        </Form.Group>
                        <Form.Group className="mb-3">
                            <Form.Label>Notes</Form.Label>
                            <Form.Control
                                as="textarea"
                                rows={3}
                                value={newStreamer.notes}
                                onChange={e => setNewStreamer(prev => ({
                                    ...prev,
                                    notes: e.target.value,
                                }))}
                                placeholder="Optional notes about this streamer"
                            />
                        </Form.Group>
                        <Form.Group className="mb-3">
                            <Form.Check
                                type="checkbox"
                                label="Active"
                                checked={newStreamer.is_active}
                                onChange={e => setNewStreamer(prev => ({
                                    ...prev,
                                    is_active: e.target.checked,
                                }))}
                            />
                        </Form.Group>
                        <Form.Group className="mb-3">
                            <Form.Check
                                type="checkbox"
                                label="Processing Enabled"
                                checked={newStreamer.processing_enabled}
                                onChange={e => setNewStreamer(prev => ({
                                    ...prev,
                                    processing_enabled: e.target.checked,
                                }))}
                            />
                        </Form.Group>
                    </Modal.Body>
                    <Modal.Footer>
                        <Button
                            variant="outline-primary"
                            onClick={() => setShowAddModal(false)}>
                            Cancel
                        </Button>
                        <Button
                            variant="primary"
                            type="submit"
                            disabled={formSubmitting || !newStreamer.twitch_username.trim()}>
                            {formSubmitting ? (
                                <>
                                    <Spinner
                                        animation="border"
                                        size="sm"
                                        className="me-2" />
                                    Adding...
                                </>
                            ) : (
                                'Add Streamer'
                            )}
                        </Button>
                    </Modal.Footer>
                </Form>
            </Modal>

            {/* Remove Streamer Confirmation Modal */}
            <Modal
                show={removeTarget !== null}
                onHide={() => setRemoveTarget(null)}>
                <Modal.Header closeButton>
                    <Modal.Title>Remove streamer</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    Are you sure you want to remove{' '}
                    <strong>{removeTarget?.twitch_username}</strong>{' '}
                    from tracking?
                </Modal.Body>
                <Modal.Footer>
                    <Button
                        variant="outline-primary"
                        onClick={() => setRemoveTarget(null)}>
                        Cancel
                    </Button>
                    <Button
                        variant="outline-danger"
                        onClick={() => handleRemoveStreamer(removeTarget?.id)}>
                        Remove
                    </Button>
                </Modal.Footer>
            </Modal>
        </>
    )
}

export default StreamerTracking
