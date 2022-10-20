FROM python:3.9-slim-buster as base

ENV FLYWHEEL=/flywheel/v0
WORKDIR ${FLYWHEEL}

RUN apt-get update
RUN apt-get install git -y
RUN python3 -m pip install --upgrade pip

COPY run requirements.txt ${FLYWHEEL}/
COPY atlases ${FLYWHEEL}/atlases/
COPY bsub_pet_quants.sh lpc_lstat.R pet_proc_bids.sh pet_quants.py run_pet_quants.sh run_sfsrr.sh submit_pet_proc_bids.sh T_template0.nii.gz ${FLYWHEEL}/


RUN pip install -r requirements.txt
RUN git clone https://github.com/ftdc-picsl/QuANTs.git
RUN chmod +x run
ENTRYPOINT ["./run"]
