"""Device routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.backend.app.api.schemas import (
    CameraConfigureRequest,
    CaptureRequest,
    CaptureResponse,
    DeviceFaultRequest,
    DeviceListResponse,
    MountGotoRequest,
    MountManualSlewRequest,
    MountTrackingRequest,
)
from apps.backend.app.core.container import AppContainer
from apps.backend.app.core.dependencies import get_container

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=DeviceListResponse)
async def list_devices(container: AppContainer = Depends(get_container)) -> DeviceListResponse:
    return DeviceListResponse(items=await container.device_service.list_devices())


@router.post("/{device_id}/connect", response_model=dict)
async def connect_device(device_id: str, container: AppContainer = Depends(get_container)) -> dict:
    result = await container.device_service.connect_device(device_id)
    return result.model_dump()


@router.post("/{device_id}/disconnect", response_model=dict)
async def disconnect_device(device_id: str, container: AppContainer = Depends(get_container)) -> dict:
    result = await container.device_service.disconnect_device(device_id)
    return result.model_dump()


@router.post("/{device_id}/fault", response_model=dict)
async def inject_fault(device_id: str, payload: DeviceFaultRequest, container: AppContainer = Depends(get_container)) -> dict:
    result = await container.device_service.inject_fault(device_id, payload.fault)
    return result.model_dump()


@router.post("/mount/manual-slew", response_model=dict)
async def manual_slew(payload: MountManualSlewRequest, container: AppContainer = Depends(get_container)) -> dict:
    result = await container.device_service.manual_slew(payload.delta_azimuth, payload.delta_altitude)
    return result.model_dump()


@router.post("/mount/goto", response_model=dict)
async def goto_mount(payload: MountGotoRequest, container: AppContainer = Depends(get_container)) -> dict:
    result = await container.device_service.goto(payload.coordinates)
    return result.model_dump()


@router.post("/mount/stop", response_model=dict)
async def stop_mount(container: AppContainer = Depends(get_container)) -> dict:
    result = await container.device_service.stop_mount()
    return result.model_dump()


@router.post("/mount/tracking", response_model=dict)
async def tracking(payload: MountTrackingRequest, container: AppContainer = Depends(get_container)) -> dict:
    result = await container.device_service.set_tracking_mode(payload.mode)
    return result.model_dump()


@router.post("/camera/configure", response_model=dict)
async def configure_camera(payload: CameraConfigureRequest, container: AppContainer = Depends(get_container)) -> dict:
    result = await container.device_service.configure_camera(payload.configuration)
    return result.model_dump()


@router.post("/camera/preview/start", response_model=dict)
async def start_preview(container: AppContainer = Depends(get_container)) -> dict:
    result = await container.device_service.start_preview()
    return result.model_dump()


@router.post("/camera/preview/stop", response_model=dict)
async def stop_preview(container: AppContainer = Depends(get_container)) -> dict:
    result = await container.device_service.stop_preview()
    return result.model_dump()


@router.post("/camera/capture", response_model=CaptureResponse)
async def capture_still(payload: CaptureRequest, container: AppContainer = Depends(get_container)) -> CaptureResponse:
    file_record, preview_record = await container.device_service.capture_still(
        session_id=payload.session_id,
        name_prefix=payload.name_prefix,
    )
    return CaptureResponse(status="ok", message="Still capture completed.", file=file_record, preview=preview_record)

