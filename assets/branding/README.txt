Water's Edition blue title wordmark

Source: waters-edition-blue.png (2149 x 732, RGBA).
Created with the native image-generation tool on 18 October 2026 using the
user's title-screen screenshot as the visual reference. This is generated
lettering inspired by the title; it is not an extracted official font.

Design brief: "WATER'S EDITION" in angular, tall fantasy lettering matching
the visual character of Tales of Eternia / Remastered, with blue marbled
texture, bright highlights, dark outlines, a cyan rim and a transparent
background. Only the new wordmark is included, not the game's original logo.

The PNG is embedded unchanged in the patch. The native renderer samples
the rectangle (36, 153)-(2113, 596), trimming transparent outer padding by
UV coordinates. Display: 124 logical pixels wide, original aspect ratio,
centered beneath Remastered. Native PNG resource ownership and unloading
are retained. See tools/title_logo_patch.py for the integration.

Version 0.10.2 adds a runtime cyan halo: sixteen low-opacity additive draws
behind the unchanged opaque face. It does not stretch or edit the source PNG.
Branding waits for the native title reveal (phase 230) and native title resource
availability, and is also visible before Start. The mod panel hides the logo.
