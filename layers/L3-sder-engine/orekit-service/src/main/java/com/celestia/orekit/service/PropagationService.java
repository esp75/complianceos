package com.celestia.orekit.service;

import com.celestia.orekit.domain.Dtos.PropagateRequest;
import com.celestia.orekit.domain.Dtos.StateDto;
import com.celestia.orekit.domain.Dtos.StateVectorResponse;
import com.celestia.orekit.error.ApiException;
import org.orekit.frames.Frame;
import org.orekit.frames.FramesFactory;
import org.orekit.propagation.analytical.tle.TLE;
import org.orekit.propagation.analytical.tle.TLEPropagator;
import org.orekit.time.AbsoluteDate;
import org.orekit.utils.PVCoordinates;
import org.springframework.stereotype.Service;

/** Propagation and frame conversion — the Orekit logic kept out of the controllers so it
 * is unit-testable without MockMvc. TLE propagation is computed in TEME (its natural frame). */
@Service
public class PropagationService {

    /** Propagate a TLE to an epoch; result expressed in TEME. */
    public StateVectorResponse propagate(PropagateRequest request) {
        TLE tle = OrekitSupport.parseTle(request.tle());
        AbsoluteDate date = OrekitSupport.parseEpoch(request.epoch());
        TLEPropagator propagator = TLEPropagator.selectExtrapolator(tle);
        Frame teme = FramesFactory.getTEME();
        PVCoordinates pv = propagator.getPVCoordinates(date, teme);
        return new StateVectorResponse(
                OrekitSupport.toKm(pv.getPosition()),
                OrekitSupport.toKm(pv.getVelocity()),
                "TEME",
                OrekitSupport.formatEpoch(date));
    }

    /** Convert a state vector between reference frames. */
    public StateVectorResponse convertFrame(StateDto state, String fromFrame, String toFrame) {
        if (state == null) {
            throw new ApiException("invalid_request", "state is required");
        }
        AbsoluteDate date = OrekitSupport.parseEpoch(state.epoch());
        Frame from = OrekitSupport.resolveFrame(fromFrame);
        Frame to = OrekitSupport.resolveFrame(toFrame);
        PVCoordinates pv = new PVCoordinates(
                OrekitSupport.fromKm(state.position()), OrekitSupport.fromKm(state.velocity()));
        PVCoordinates converted = from.getTransformTo(to, date).transformPVCoordinates(pv);
        return new StateVectorResponse(
                OrekitSupport.toKm(converted.getPosition()),
                OrekitSupport.toKm(converted.getVelocity()),
                toFrame.trim().toUpperCase(),
                OrekitSupport.formatEpoch(date));
    }
}
