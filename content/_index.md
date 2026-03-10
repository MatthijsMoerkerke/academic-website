---
title: 'Matthijs Moerkerke'
summary: ''
date: 2024-01-01
type: landing

design:
  spacing: '6rem'

sections:

  - block: resume-biography-3
    content:
      username: MatthijsMoerkerke

      text: |
        I am a **postdoctoral researcher at Ghent University (Department of Rehabilitation Sciences)** and voluntary research fellow at **KU Leuven – Center for Developmental Psychiatry**.

        My research focuses on **neurophysiology, pain science, and neuroendocrine mechanisms**, with particular interest in the role of **oxytocin in autism and pain-related processes**.

        I investigate how **stress physiology, neuroendocrine signaling, and brain mechanisms interact with behavior and clinical outcomes**, combining neuroimaging, EEG, physiological recordings, and clinical trial methodologies.

        My work aims to translate neurobiological insights into **improved diagnostics, treatment strategies, and rehabilitation approaches** for neurological and neurodevelopmental conditions.

      button:
        text: Download CV
        url: uploads/resume.pdf

      headings:
        about: About
        education: Education
        interests: Research Interests

    design:
      background:
        gradient_mesh:
          enable: true

      name:
        size: md

      avatar:
        size: medium
        shape: circle

  - block: markdown
    content:
      title: Research
      text: |
        My research lies at the intersection of **neuroscience, rehabilitation sciences, and clinical neurophysiology**.

        I study the **neurobiological mechanisms underlying autism, pain, and stress regulation**, with a particular focus on **oxytocin signaling and brain–body interactions**.

        Current projects examine:

        - Neuroendocrine modulation of pain and stress
        - Neural mechanisms of autism and social cognition
        - Physiological biomarkers of chronic pain
        - Multimodal integration of neuroimaging and physiological signals

        My research integrates **clinical trials, EEG, neuroimaging, and physiological measurements** to better understand how biological systems contribute to behavior and clinical outcomes.
  
  - block: markdown
    content:
      title: Academic Service & Leadership
      text: |
        - Steering-group member, Pain in Motion (PIM) international research consortium
        - Expert panel member, Active Monitoring of Oxytocin Research Evidence (AMORE), University of Oslo
        - Program & award manager, Pain Science in Motion Conference 2026
        - Ad hoc grant reviewer, Foundation for Prader–Willi Research

        Member of:
        - International Association for the Study of Pain (IASP)
        - International Society for Autism Research (INSAR)
        - Belgian Association for Psychological Sciences (BAPS)

  - block: collection
    id: papers
    content:
      title: Featured Publications
      filters:
        folders:
          - publications/journal-article
          - publications/conference-paper
          - publications/preprint
        featured_only: true
    design:
      view: article-grid
      columns: 2

  - block: collection
    content:
      title: Publications
      filters:
        folders:
          - publications/journal-article
          - publications/conference-paper
          - publications/preprint
    design:
      view: citation

  - block: collection
    id: talks
    content:
      title: Talks & Presentations
      filters:
        folders:
          - events
    design:
      view: card


---
