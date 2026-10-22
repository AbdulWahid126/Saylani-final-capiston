"""High-level orchestration service for AI Chart Screenshot Analysis (TASK-014).

Coordinates image validation, vision model analysis, personal playbook RAG cross-referencing,
risk geometry validation, badge taxonomy, and database persistence under strict tenancy.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundException
from app.models.vision import ChartAnalysis
from app.schemas.common import DataClassificationBadge
from app.schemas.reviewer import TradeDirection
from app.schemas.vision import (
    ChartAnalysisResponse,
    ChartType,
    KeyLevelObservation,
    LevelType,
    MarketStructureObservation,
    PlaybookCitationItem,
    ScenarioAnalysis,
    StrategyMode,
    TradeSetupObservation,
    TrendDirection,
    VisionBadge,
)
from app.services.image_validator import validate_and_process_chart_image
from app.services.rag_engine import search_playbook_chunks
from app.services.vision_provider import get_vision_provider


async def analyze_chart_screenshot(
    db: AsyncSession,
    user_id: uuid.UUID,
    file_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
    strategy_mode: StrategyMode = StrategyMode.GENERAL,
    custom_prompt: str | None = None,
    include_playbook: bool = True,
    persist: bool = True,
) -> ChartAnalysisResponse:
    """Executes end-to-end chart screenshot analysis pipeline."""
    # 1. Image Validation & Re-encoding (Decompression bomb & payload safe)
    validated_img = validate_and_process_chart_image(
        file_bytes=file_bytes,
        original_filename=filename,
        content_type=content_type,
    )
    dim_str = f"{validated_img.width}x{validated_img.height}"

    # 2. Vision Model Technical Extraction
    provider = get_vision_provider()
    raw_analysis = await provider.analyze_chart(
        image=validated_img,
        strategy_mode=strategy_mode,
        custom_prompt=custom_prompt,
    )

    symbol = raw_analysis.get("symbol")
    timeframe = raw_analysis.get("timeframe")
    chart_type_val = raw_analysis.get("chart_type", ChartType.UNKNOWN.value)
    chart_type = (
        ChartType(chart_type_val)
        if chart_type_val in ChartType._value2member_map_
        else ChartType.UNKNOWN
    )

    limitations: list[str] = list(raw_analysis.get("limitations") or [])
    badge_strings: list[str] = list(raw_analysis.get("badges") or [])

    # 3. Personal Playbook Knowledge Base Cross-Referencing (TASK-012)
    playbook_citations: list[PlaybookCitationItem] = []
    if include_playbook:
        search_query = f"{symbol or 'chart'} {strategy_mode.value} technical setup rules"
        matched_chunks = await search_playbook_chunks(
            db=db,
            user_id=user_id,
            query=search_query,
            top_k=3,
            similarity_threshold=0.10,
        )
        if matched_chunks:
            has_conflict = False
            for chunk in matched_chunks:
                p_num = chunk.chunk_metadata.get("page")
                cit_str = f"{chunk.document_filename}" + (f" (Page {p_num})" if p_num else "")
                first_line = chunk.content.strip().split("\n")[0][:120]

                # Cross-check stop loss rule against trade setup if present
                content_lower = chunk.content.lower()
                trade_setup_raw = raw_analysis.get("trade_setup")
                if trade_setup_raw and not trade_setup_raw.get("stop_loss"):
                    if "stop loss" in content_lower or "invalidation" in content_lower:
                        has_conflict = True

                playbook_citations.append(
                    PlaybookCitationItem(
                        document_filename=chunk.document_filename,
                        page=p_num,
                        chunk_id=str(chunk.chunk_id),
                        rule_summary=first_line,
                        citation=cit_str,
                        relevance_notes=f"Retrieved from user playbook for {strategy_mode.value} setup verification.",
                    )
                )

            if has_conflict:
                if VisionBadge.PLAYBOOK_CONFLICT.value not in badge_strings:
                    badge_strings.append(VisionBadge.PLAYBOOK_CONFLICT.value)
                limitations.append(
                    "Playbook Rule Conflict: User playbook mandates stop loss, but none was detected on chart."
                )
            else:
                if VisionBadge.PLAYBOOK_ALIGNED.value not in badge_strings:
                    badge_strings.append(VisionBadge.PLAYBOOK_ALIGNED.value)
        else:
            limitations.append("No personal playbook documents retrieved for this specific setup.")

    # 4. Parse Market Structure & Geometry Checks
    ms_raw = raw_analysis.get("market_structure") or {}
    bias_val = ms_raw.get("overall_bias", TrendDirection.UNCERTAIN.value)
    bias_enum = (
        TrendDirection(bias_val)
        if bias_val in TrendDirection._value2member_map_
        else TrendDirection.UNCERTAIN
    )
    market_structure = MarketStructureObservation(
        overall_bias=bias_enum,
        trend_description=ms_raw.get("trend_description", "Trend structure observed from chart."),
        recent_swing_high=ms_raw.get("recent_swing_high"),
        recent_swing_low=ms_raw.get("recent_swing_low"),
        structure_break_observed=bool(ms_raw.get("structure_break_observed", False)),
        structure_break_type=ms_raw.get("structure_break_type"),
    )

    # 5. Parse Key Levels
    key_levels: list[KeyLevelObservation] = []
    for kl in raw_analysis.get("key_levels") or []:
        l_type_val = kl.get("level_type", LevelType.OTHER.value)
        l_type = (
            LevelType(l_type_val) if l_type_val in LevelType._value2member_map_ else LevelType.OTHER
        )
        key_levels.append(
            KeyLevelObservation(
                level_type=l_type,
                price_estimate=kl.get("price_estimate"),
                price_annotation=kl.get("price_annotation"),
                is_annotated=bool(kl.get("is_annotated", False)),
                description=kl.get("description", "Identified level zone"),
                confidence=float(kl.get("confidence", 0.5)),
            )
        )

    # 6. Parse Trade Setup & Geometry Verification
    trade_setup = None
    ts_raw = raw_analysis.get("trade_setup")
    if ts_raw:
        dir_val = ts_raw.get("direction")
        dir_enum = TradeDirection(dir_val) if dir_val in TradeDirection._value2member_map_ else None
        entry_p = ts_raw.get("entry_price")
        sl_p = ts_raw.get("stop_loss")
        tp_p = ts_raw.get("take_profit")

        # Inverted price geometry validation
        if entry_p and sl_p and tp_p:
            entry_f, sl_f, tp_f = float(entry_p), float(sl_p), float(tp_p)
            if dir_enum == TradeDirection.BUY and not (tp_f > entry_f > sl_f):
                limitations.append(
                    f"Warning: Inverted trade geometry for BUY setup (Entry: {entry_f}, SL: {sl_f}, TP: {tp_f})."
                )
            elif dir_enum == TradeDirection.SELL and not (sl_f > entry_f > tp_f):
                limitations.append(
                    f"Warning: Inverted trade geometry for SELL setup (Entry: {entry_f}, SL: {sl_f}, TP: {tp_f})."
                )

        trade_setup = TradeSetupObservation(
            direction=dir_enum,
            entry_price=entry_p,
            stop_loss=sl_p,
            take_profit=tp_p,
            is_annotated=bool(ts_raw.get("is_annotated", False)),
            notes=ts_raw.get("notes"),
        )

    # 7. Scenarios
    bull_raw = raw_analysis.get("bullish_scenario") or {}
    bullish_scenario = ScenarioAnalysis(
        scenario_name=bull_raw.get("scenario_name", "Bullish Scenario"),
        rationale=bull_raw.get("rationale", "Observable bullish technical indications."),
        trigger_condition=bull_raw.get("trigger_condition"),
        invalidation_condition=bull_raw.get("invalidation_condition"),
        target_level=bull_raw.get("target_level"),
        confidence=float(bull_raw.get("confidence", 0.5)),
    )

    bear_raw = raw_analysis.get("bearish_scenario") or {}
    bearish_scenario = ScenarioAnalysis(
        scenario_name=bear_raw.get("scenario_name", "Bearish Scenario"),
        rationale=bear_raw.get("rationale", "Observable bearish technical indications."),
        trigger_condition=bear_raw.get("trigger_condition"),
        invalidation_condition=bear_raw.get("invalidation_condition"),
        target_level=bear_raw.get("target_level"),
        confidence=float(bear_raw.get("confidence", 0.5)),
    )

    # 8. Uncertainty & Badges
    uncertainty = float(raw_analysis.get("uncertainty_rating", 0.2))
    if not symbol or not timeframe:
        uncertainty = min(1.0, uncertainty + 0.2)
        if VisionBadge.UNVERIFIED_LEVELS.value not in badge_strings:
            badge_strings.append(VisionBadge.UNVERIFIED_LEVELS.value)

    # Filter unique badges in taxonomy
    final_badges = [
        VisionBadge(b) for b in dict.fromkeys(badge_strings) if b in VisionBadge._value2member_map_
    ]
    if not final_badges:
        final_badges = [VisionBadge.AI_INTERPRETATION, VisionBadge.OBSERVED_PATTERN]

    # 9. Build Response Object
    now_utc = datetime.now(UTC)
    analysis_id = uuid.uuid4()
    exec_summary = raw_analysis.get("executive_summary") or (
        f"{strategy_mode.value} CHART ANALYSIS: Visual appraisal of {symbol or 'unidentified asset'} on {timeframe or 'unspecified timeframe'}. "
        f"Bias is {market_structure.overall_bias.value}."
    )

    resp = ChartAnalysisResponse(
        id=analysis_id,
        user_id=user_id,
        strategy_mode=strategy_mode,
        symbol=symbol,
        timeframe=timeframe,
        chart_type=chart_type,
        image_filename=validated_img.sanitized_filename,
        image_dimensions=dim_str,
        market_structure=market_structure,
        key_levels=key_levels,
        trade_setup=trade_setup,
        bullish_scenario=bullish_scenario,
        bearish_scenario=bearish_scenario,
        playbook_citations=playbook_citations,
        limitations=list(dict.fromkeys(limitations)),
        badges=final_badges,
        uncertainty_rating=min(1.0, max(0.0, round(uncertainty, 2))),
        executive_summary=exec_summary,
        data_classification_badge=DataClassificationBadge.AI_INTERPRETATION,
        created_at=now_utc,
    )

    # 10. Persistence
    if persist:
        record = ChartAnalysis(
            id=resp.id,
            user_id=user_id,
            strategy_mode=resp.strategy_mode.value,
            symbol=resp.symbol,
            timeframe=resp.timeframe,
            chart_type=resp.chart_type.value,
            image_filename=resp.image_filename,
            image_dimensions=resp.image_dimensions,
            market_structure=resp.market_structure.model_dump(mode="json"),
            key_levels=[kl.model_dump(mode="json") for kl in resp.key_levels],
            trade_setup=resp.trade_setup.model_dump(mode="json") if resp.trade_setup else None,
            scenarios={
                "bullish_scenario": resp.bullish_scenario.model_dump(mode="json"),
                "bearish_scenario": resp.bearish_scenario.model_dump(mode="json"),
            },
            playbook_citations=[pc.model_dump(mode="json") for pc in resp.playbook_citations],
            limitations=resp.limitations,
            badges=[b.value for b in resp.badges],
            uncertainty_rating=resp.uncertainty_rating,
            executive_summary=resp.executive_summary,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db.add(record)
        await db.commit()

    return resp


async def list_user_chart_analyses(
    db: AsyncSession,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
) -> list[ChartAnalysisResponse]:
    """Retrieves paginated historical chart analyses strictly owned by current user."""
    stmt = (
        select(ChartAnalysis)
        .where(ChartAnalysis.user_id == user_id)
        .order_by(desc(ChartAnalysis.created_at))
        .offset(skip)
        .limit(limit)
    )
    records = (await db.scalars(stmt)).all()
    return [_map_record_to_response(rec) for rec in records]


async def get_user_chart_analysis(
    db: AsyncSession,
    user_id: uuid.UUID,
    analysis_id: uuid.UUID,
) -> ChartAnalysisResponse:
    """Retrieves a single chart analysis by ID ensuring strict multi-tenant ownership."""
    stmt = select(ChartAnalysis).where(
        ChartAnalysis.id == analysis_id,
        ChartAnalysis.user_id == user_id,
    )
    record = (await db.scalars(stmt)).first()
    if not record:
        raise NotFoundException(f"Chart analysis '{analysis_id}' was not found or is unauthorized.")
    return _map_record_to_response(record)


async def delete_user_chart_analysis(
    db: AsyncSession,
    user_id: uuid.UUID,
    analysis_id: uuid.UUID,
) -> None:
    """Deletes a chart analysis ensuring strict multi-tenant ownership."""
    stmt = select(ChartAnalysis).where(
        ChartAnalysis.id == analysis_id,
        ChartAnalysis.user_id == user_id,
    )
    record = (await db.scalars(stmt)).first()
    if not record:
        raise NotFoundException(f"Chart analysis '{analysis_id}' was not found or is unauthorized.")
    await db.delete(record)
    await db.commit()


def _map_record_to_response(rec: ChartAnalysis) -> ChartAnalysisResponse:
    """Maps SQLAlchemy model to Pydantic response schema."""
    scenarios = rec.scenarios or {}
    bullish = scenarios.get("bullish_scenario") or {
        "scenario_name": "Bullish Scenario",
        "rationale": "Historical scenario record",
        "confidence": 0.5,
    }
    bearish = scenarios.get("bearish_scenario") or {
        "scenario_name": "Bearish Scenario",
        "rationale": "Historical scenario record",
        "confidence": 0.5,
    }

    badges_enums = [
        VisionBadge(b) for b in (rec.badges or []) if b in VisionBadge._value2member_map_
    ]
    if not badges_enums:
        badges_enums = [VisionBadge.AI_INTERPRETATION, VisionBadge.OBSERVED_PATTERN]

    return ChartAnalysisResponse(
        id=rec.id,
        user_id=rec.user_id,
        strategy_mode=StrategyMode(rec.strategy_mode)
        if rec.strategy_mode in StrategyMode._value2member_map_
        else StrategyMode.GENERAL,
        symbol=rec.symbol,
        timeframe=rec.timeframe,
        chart_type=ChartType(rec.chart_type)
        if rec.chart_type in ChartType._value2member_map_
        else ChartType.UNKNOWN,
        image_filename=rec.image_filename,
        image_dimensions=rec.image_dimensions,
        market_structure=MarketStructureObservation.model_validate(rec.market_structure or {}),
        key_levels=[KeyLevelObservation.model_validate(kl) for kl in (rec.key_levels or [])],
        trade_setup=TradeSetupObservation.model_validate(rec.trade_setup)
        if rec.trade_setup
        else None,
        bullish_scenario=ScenarioAnalysis.model_validate(bullish),
        bearish_scenario=ScenarioAnalysis.model_validate(bearish),
        playbook_citations=[
            PlaybookCitationItem.model_validate(pc) for pc in (rec.playbook_citations or [])
        ],
        limitations=rec.limitations or [],
        badges=badges_enums,
        uncertainty_rating=rec.uncertainty_rating,
        executive_summary=rec.executive_summary,
        data_classification_badge=DataClassificationBadge.AI_INTERPRETATION,
        created_at=rec.created_at,
    )
